# Deployment Guide: как собрать PKI за $129

## Предисловие: это не инструкция, это путешествие

Большинство deployment guide — это список команд: скопируй, вставь, не думай. Этот — другой. Каждый шаг объясняет не только «что делать», но и «почему именно так». Потому что когда через два года что-то сломается в три часа ночи — понимание «почему» спасёт быстрее, чем копипаста «что».

Десять шагов, от голого железа до первого сертификата. Каждый шаг — checkpoint: если что-то пошло не так, можно остановиться и разобраться, не откатывая всё.

---


## Целевая платформа: что мы собираем

| Компонент | Модель | Цена | Зачем |
|-----------|--------|------|-------|
| SBC | Firefly AIO-RK3328-JD4 | ~$111 | Мозг: Linux, Python, PKI Core |
| MCU | WeAct STM32G474CEU Mini | ~$18 | Сердце: аппаратный TRNG |
| USB | Кабель Micro-USB | ~$0 | Артерия: энтропия от MCU к SBC |
| Итого | | ~$129 | Полноценная PKI с аппаратным TRNG |

Почему Firefly, а не Raspberry Pi? Три причины. Первая — промышленная доступность: Firefly гарантирует производство минимум 5 лет, Pi — нет (вспомните дефицит 2021-2023). Вторая — eMMC вместо SD-карты: SD-карты деградируют при частой записи (логи, БД), eMMC — нет. Третья — Rockchip BSP с полной поддержкой SELinux и eBPF в ядре 5.10.

Почему STM32G474, а не G431 или H750? G474 — золотая середина: 512KB Flash (запас для будущих фич), 128KB RAM (достаточно для USB stack + буферы), тот же Cortex-M4 что и G431 (совместимость бинарей в рамках G4 семейства). G431 — бюджетнее, но 128KB Flash впритык. H750 — мощнее, но другой HAL, другая сборка.

---

## Шаг 1: Подготовка ядра — фундамент безопасности

Ядро — это не «просто Linux». Это первый слой защиты, и от его конфигурации зависит, будут ли работать SELinux и eBPF.

Стандартное ядро Rockchip BSP не включает SELinux. Нужна пересборка с кастомным defconfig:

```bash
# Ключевые опции (уже включены в наш defconfig):
# CONFIG_SECURITY_SELINUX=y      <- MAC
# CONFIG_BPF=y                   <- eBPF framework
# CONFIG_BPF_SYSCALL=y           <- bpf() syscall
# CONFIG_USB_HIDDEV=y            <- USB HID device support
```

Четыре строки конфига, но без любой из них — целый слой защиты не работает. Без `SECURITY_SELINUX` — нет доменной изоляции. Без `BPF` — нет сетевого фильтра и syscall аудита. Без `USB_HIDDEV` — нет аппаратного TRNG.

Отдельный патч — USB2 PHY fix для RK3328. Без него USB HID устройства не определяются стабильно после горячего подключения. Баг в Rockchip BSP: PHY не сбрасывается корректно при re-enumeration. Патч — 12 строк в DTS, но без него STM32 может «пропасть» после перезагрузки хоста.

Checkpoint: после прошивки ядра — `uname -r` должен показать кастомную версию, `cat /sys/fs/selinux/enforce` должен вернуть `1` (или `0` если ещё не настроен), `ls /sys/fs/bpf/` должен показать пустую директорию.

---

## Шаг 2: Прошивка STM32 — рождение генератора

STM32 — это не периферия, которую «подключил и забыл». Это отдельный компьютер с собственной прошивкой, который нужно запрограммировать.

```bash
# Требования: PlatformIO CLI + CMSIS-DAP адаптер (ST-Link, J-Link, или DAPLink)

# Прошить G474 (default)
pio run -e weact_g474ceu -t upload

# Или G431
pio run -e weact_g431cbu -t upload

# Или H750
pio run -e weact_h750vbt -t upload
```

Одна команда — но за ней: компиляция C-кода, линковка с HAL, генерация бинаря, загрузка через SWD (Serial Wire Debug), верификация. PlatformIO делает всё это прозрачно.

После прошивки MCU перезагружается и проходит startup test (TSR-1). Если светодиод мигает быстро (100ms) — firmware работает, USB активен. Если мигает SOS (три коротких, три длинных, три коротких) — ошибка инициализации, код ошибки можно прочитать через SWD отладчик.

Проверка на хосте:

```bash
lsusb | grep 0483:5750
# Bus 001 Device 003: ID 0483:5750 STMicroelectronics ...

ls /dev/hidraw*
# /dev/hidraw0
```

Если `lsusb` не показывает устройство — проверить USB-кабель (некоторые кабели — только зарядка, без данных). Если показывает, но `/dev/hidraw0` нет — проблема с ядром (нет `CONFIG_USB_HIDDEV`).

Checkpoint: `lsusb` видит 0483:5750, `/dev/hidraw0` существует.

---

## Шаг 3: Подготовка RK3328 — создание среды обитания

PKI-сервис работает от непривилегированного пользователя `pki`. Не от root, не от `admin` — от специального системного пользователя без shell, без home directory, без возможности логина.

```bash
sudo useradd -r -s /sbin/nologin pki
sudo mkdir -p /opt/pki-on-box/{app,data,logs,venv}
sudo mkdir -p /var/lib/pki/{keys,certs,certs/by_label}
sudo mkdir -p /var/log/pki-box
sudo mkdir -p /etc/pki-box
sudo chown -R pki:pki /opt/pki-on-box /var/lib/pki /var/log/pki-box /etc/pki-box
```

Шесть директорий, каждая со своим назначением:

- `/opt/pki-on-box/app/` — код приложения. Read-only в runtime, обновляется только через deploy.
- `/opt/pki-on-box/venv/` — Python virtualenv. Изолирует зависимости от системного Python.
- `/var/lib/pki/keys/` — зашифрованные приватные ключи (.enc файлы). Самая чувствительная директория.
- `/var/lib/pki/certs/` — PEM сертификаты + `by_label/` индекс.
- `/var/log/pki-box/` — логи. Append-only в SELinux.
- `/etc/pki-box/` — конфигурация. Read-only для сервисов.

Почему `/opt`, а не `/usr/local`? Потому что `ProtectSystem=strict` в systemd делает `/usr` read-only. `/opt` — стандартное место для third-party приложений, и systemd позволяет `ReadWritePaths=/opt/pki-on-box/data,/opt/pki-on-box/logs`.

Checkpoint: `ls -la /var/lib/pki/` показывает директории, владелец `pki:pki`.

---

## Шаг 4: Python virtualenv — изоляция зависимостей

Python 3.6 на RK3328 — это системный Python. Ставить пакеты в него — путь к конфликтам. Virtualenv изолирует зависимости PKI от системы.

```bash
sudo -u pki python3 -m venv /opt/pki-on-box/venv
sudo -u pki /opt/pki-on-box/venv/bin/pip install -r deploy/requirements-rk3328.txt
```

18 пакетов, каждый pinned на конкретную версию. Не `cryptography>=3.0`, а `cryptography==3.4.8`. Почему? Потому что `cryptography` 3.4.8 — последняя версия с поддержкой Python 3.6. Версия 37.0+ требует Python 3.7+. Один непинованный пакет — и `pip install` сломается через полгода, когда выйдет новая версия.

Ключевые зависимости и почему именно эти версии:

| Пакет | Версия | Почему эта версия |
|-------|--------|------------------|
| cryptography | 3.4.8 | Последняя для Python 3.6. X.509, OpenSSL bindings |
| flask | 2.0.3 | Последняя для Python 3.6. REST API |
| click | 8.0.4 | Последняя для Python 3.6. CLI framework |
| hidapi | 0.14.0 | USB HID. Требует libhidapi-dev на ARM64 |
| pyyaml | 6.0 | Config parsing. Без C-extensions на ARM64 — медленнее, но работает |

`hidapi` — особый случай. Это Python-обёртка над C-библиотекой `libhidapi`. На ARM64 нужен `libhidapi-dev` в системе: `sudo apt install libhidapi-dev`. Без него `pip install hidapi` скомпилирует C-extension, но не найдёт header files.

Checkpoint: `/opt/pki-on-box/venv/bin/python -c "import cryptography; print(cryptography.__version__)"` → `3.4.8`.

---

## Шаг 5: Конфигурация — одна правда в одном файле

```bash
sudo cp deploy/config.example.yaml /etc/pki-box/config.yaml
sudo chown pki:pki /opt/pki-on-box/config.yaml
```

Минимальный конфиг для production:

```yaml
trng:
  mode: hardware          # НЕ auto — в production только hardware
  hid_vid: "0x0483"
  hid_pid: "0x5750"

drbg:
  algorithm: hmac-sha256
  reseed_interval: 1000   # reseed каждые 1000 генераций

crypto:
  rsa_key_size: 4096      # для CA. Серверные сертификаты override на 2048
  ec_curve: P-384

storage:
  path: /var/lib/pki
  db_path: /var/lib/pki/pki.db
  certs_path: /var/lib/pki/certs
  ca_key_password: "<CHANGE_ME>"  # ОБЯЗАТЕЛЬНО сменить!

api:
  host: "127.0.0.1"       # только localhost — сеть через eBPF
  port: 5000
```

`mode: hardware` — не `auto`. В production STM32 должен быть подключён. Если он отключится — система должна упасть, а не молча переключиться на `os.urandom`. Это разница между «мы гарантируем аппаратную энтропию» и «мы надеемся на аппаратную энтропию».

`host: "127.0.0.1"` — Flask слушает только localhost. Внешний доступ — через reverse proxy или напрямую через eBPF whitelist. Никогда `0.0.0.0` в production.

`ca_key_password: "<CHANGE_ME>"` — пароль для шифрования ключей CA. Это единственный секрет, который нужно запомнить. Всё остальное (ключи, сертификаты, БД) можно восстановить из бэкапа. Пароль — нет.

Checkpoint: `cat /etc/pki-box/config.yaml | grep mode` → `hardware`.

---

## Шаг 6: Загрузка приложения

```bash
sudo -u pki cp -r asw/PKI/* /opt/pki-on-box/app/
```

Одна команда — весь Python-код на месте. Никакого `pip install` самого приложения, никакого `setup.py` — просто копирование файлов. Это осознанное решение: чем проще deploy — тем проще rollback. `cp -r` в одну сторону, `rm -rf && cp -r app.prev` в другую.

Checkpoint: `ls /opt/pki-on-box/app/core/` показывает `crypto_engine.py`, `drbg.py`, `trng.py`, `key_storage.py`, `self_tests.py`.

---

## Шаг 7: systemd сервисы — запуск под контролем

```bash
sudo cp bsw/systemd/pki.service /etc/systemd/system/
sudo cp bsw/systemd/hsm.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable pki.service
```

Два сервиса, не один. `pki.service` — PKI Core (REST API + бизнес-логика). `hsm.service` — HSM/TRNG мост (USB HID + энтропия). Разделение — не для удобства, а для изоляции: разные SELinux домены, разные capabilities, разные ограничения.

Зависимости:

```
pki.service
  After=network.target
  Wants=pki-hsm.service
  → Стартует после сети, хочет HSM (но не требует)

hsm.service
  After=pki.service
  BindsTo=pki.service
  → Стартует после PKI, умирает вместе с PKI
```

`Wants` vs `Requires`: PKI Core хочет HSM, но может работать без него (в режиме `auto` переключится на software TRNG). В production с `mode: hardware` — упадёт при первом запросе энтропии. Но systemd не будет блокировать старт.

`BindsTo`: если PKI Core остановлен — HSM тоже останавливается. Нет смысла стримить энтропию, если некому её потреблять.

Checkpoint: `systemctl status pki.service` → `enabled`, `inactive (dead)` (ещё не запущен).

---

## Шаг 8: SELinux — надеваем броню

```bash
cd bsw/selinux
make -f /usr/share/selinux/devel/Makefile pki_box.pp
sudo semodule -i pki_box.pp
sudo restorecon -Rv /opt/pki-on-box /var/lib/pki /var/log/pki-box /etc/pki-box
```

Три команды: компиляция модуля, установка, применение контекстов. После этого каждый файл в `/var/lib/pki` имеет тип `pki_var_t`, каждый лог — `pki_log_t`, каждый конфиг — `pki_config_t`.

Проверка:

```bash
ls -Z /var/lib/pki/
# unconfined_u:object_r:pki_var_t:s0 keys
# unconfined_u:object_r:pki_var_t:s0 certs
# unconfined_u:object_r:pki_var_t:s0 pki.db

getenforce
# Enforcing
```

Если `getenforce` возвращает `Permissive` — SELinux логирует нарушения, но не блокирует. Для тестирования — нормально. Для production — `sudo setenforce 1`.

Если после `restorecon` контексты не применились — проверить `semanage fcontext -l | grep pki`. Если пусто — модуль не установился. `semodule -l | grep pki_box` должен показать модуль.

Checkpoint: `ls -Z /var/lib/pki/keys/` показывает `pki_var_t`.

---

## Шаг 9: eBPF фильтры — невидимая защита

```bash
clang -O2 -target bpf -c bsw/ebpf/network_filter.c -o /opt/pki-on-box/network_filter.o
clang -O2 -target bpf -c bsw/ebpf/syscall_filter.c -o /opt/pki-on-box/syscall_filter.o
```

Компиляция C в BPF байткод. `-target bpf` — это не x86 и не ARM, это виртуальная машина ядра. BPF verifier проверит программу при загрузке: завершается ли она, не обращается ли к невалидной памяти, не содержит ли бесконечных циклов.

Загрузка — через `bpftool` или custom loader в `SecurityManager.initialize_security()`. При старте PKI Core `SecurityManager` проверяет capabilities (`has_ebpf`, `has_bpftool`) и загружает программы если возможно. Если нет — логирует warning и продолжает. eBPF — дополнительный слой, не обязательный.

Checkpoint: `bpftool prog list | grep pki` — после первого запуска PKI Core.

---

## Шаг 10: Первый запуск — момент истины

```bash
sudo systemctl start pki.service
```

Одна команда — и начинается цепочка из Sequence Diagram #1 (Startup): загрузка конфига → KAT (6 тестов) → инициализация TRNG → DRBG instantiate → health check → Flask ready.

Проверка:

```bash
# Статус сервисов
sudo systemctl status pki.service hsm.service

# Health check
curl http://127.0.0.1:5000/api/v1/health
# {"status": "ok"}

# Логи — TRNG инициализирован?
journalctl -u pki.service | grep TRNG
# TRNG health check passed

# Логи — KAT прошли?
journalctl -u pki.service | grep KAT
# KAT: all 6 tests passed
```

Если `health` не отвечает — `journalctl -u pki.service -n 50`. Типичные проблемы:
- `CryptoSelfTestError` — OpenSSL повреждён или несовместимая версия `cryptography`
- `TRNGDeviceError` — STM32 не найден (mode=hardware, но USB не подключён)
- `Permission denied: /dev/hidraw0` — HSM Service не имеет доступа (проверить DeviceAllow в unit file)
- `Address already in use: 5000` — порт занят другим процессом

Checkpoint: `curl localhost:5000/api/v1/health` → `{"status": "ok"}`.

---

## Бонус: первая церемония Root CA

Система работает, но PKI пуста. Нужен Root CA — корень доверия.

```bash
cd /opt/pki-on-box/app
/opt/pki-on-box/venv/bin/python pki.py ca create-root \
  --name "PKI-Box Root CA" \
  --validity 20
```

20 лет. RSA-4096. Self-signed. Ключ зашифрован AES-256-GCM и сохранён в `/var/lib/pki/keys/ca_pki_box_root_ca.enc`. Сертификат — в SQLite и в `/var/lib/pki/certs/`.

Затем — Intermediate CA:

```bash
/opt/pki-on-box/venv/bin/python pki.py ca create-intermediate \
  --name "PKI-Box Intermediate CA 1" \
  --parent ca_pki_box_root_ca \
  --validity 10
```

10 лет. RSA-4096. Подписан Root CA. `pathlen=0` — не может создавать под-CA.

Проверка:

```bash
/opt/pki-on-box/venv/bin/python pki.py ca list
# ca_pki_box_root_ca          PKI-Box Root CA              2026-04-10
# ca_pki_box_intermediate_ca_1  PKI-Box Intermediate CA 1  2026-04-10
```

Два CA — система готова выпускать сертификаты.

---

## Послесловие: что дальше

Система развёрнута, Root CA создан, Intermediate CA готов. Дальше — рутина: выпуск сертификатов через REST API или CLI, периодическая генерация CRL, мониторинг через health check.

Но есть вещи, которые стоит сделать до того, как система уйдёт в production:

1. Сменить `ca_key_password` с `<CHANGE_ME>` на что-то, что вы запомните и никому не скажете.
2. Сделать бэкап `/var/lib/pki/keys/` — зашифрованные ключи CA. Потеря этих файлов = потеря PKI.
3. Записать fingerprint Root CA сертификата — это единственный способ верифицировать, что Root CA не подменён.
4. Настроить мониторинг: `curl localhost:5000/api/v1/health` каждые 5 минут, алерт если не `ok`.
5. Запланировать ротацию Intermediate CA через 5 лет (не 10 — с запасом).

$129, 10 шагов, одна церемония — и у вас PKI с аппаратным TRNG, SELinux изоляцией и eBPF фильтрацией. Не Thales Luna за $15,000, но для IoT-фермы, внутренней инфраструктуры или образовательных целей — более чем.
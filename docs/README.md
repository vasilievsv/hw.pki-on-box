# 📚 PKI-on-Box — Документация

> Архитектурная документация проекта в нарративном стиле.
> Каждый документ объясняет не только «что», но и «почему» — мотивация решений, компромиссы, модели угроз.

## Порядок чтения

Документы выстроены от общего к частному — как zoom камеры: сначала система целиком, потом внутренности, потом детали.

| # | Документ | Уровень | О чём |
|---|----------|---------|-------|
| 1 | [C4 Context](C4_CONTEXT.md) | Система | Кто взаимодействует с PKI-on-Box и зачем. 4 актора, 3 границы доверия |
| 2 | [C4 Container](C4_CONTAINER.md) | Внутренности | Что внутри: 5 слоёв, 16 компонентов, путь запроса через 11 шагов |
| 3 | [Component Overview](COMPONENT_OVERVIEW.md) | Анатомия | Каждый компонент: зачем существует, как работает, почему именно так |
| 4 | [Class Diagram](CLASS_DIAGRAM_PKI.md) | Классы | 14 классов, 5 слоёв, цепочка доверия от теплового шума к сертификату |
| 5 | [Sequence Flows](SEQUENCE_PKI_FLOW.md) | Время | 5 историй: startup, ceremony, issuance, revocation, entropy chain |
| 6 | [Deployment Diagram](DEPLOYMENT_DIAGRAM.md) | Железо | 3 мира (Workstation, STM32, RK3328), USB как слабое звено, $129 |
| 7 | [Deployment Guide](DEPLOYMENT_GUIDE.md) | Практика | 10 шагов от голого железа до первого сертификата |

## Быстрый вход

- **«Что это за система?»** → начни с [C4 Context](C4_CONTEXT.md)
- **«Как устроена внутри?»** → [C4 Container](C4_CONTAINER.md) → [Component Overview](COMPONENT_OVERVIEW.md)
- **«Хочу развернуть»** → сразу в [Deployment Guide](DEPLOYMENT_GUIDE.md)
- **«Как работает криптография?»** → [Sequence Flows](SEQUENCE_PKI_FLOW.md), раздел Entropy Chain
- **«Какие классы, какие зависимости?»** → [Class Diagram](CLASS_DIAGRAM_PKI.md)



# api/cli.py
import click

@click.group()
def pki_cli():
    """CLI для управления учебным PKI"""
    pass

@pki_cli.command()
@click.option('--name', required=True, help='CA name')
@click.option('--validity', default=10, help='Validity in years')
def create_root_ca(name, validity):
    """Создание корневого ЦС"""
    # Реализация через сервисы
    pass
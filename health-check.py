#!/usr/bin/python3
import click
import json
import os
import subprocess

from datetime import datetime
from discord_webhook import DiscordWebhook, DiscordEmbed

# info = {
#   'alive': bool,
#   'last-alive': str,
#   'nickname': str
# }

TIME_FMT = '%Y-%m-%d %H:%M:%S'
WEBHOOK_URL = ''


def read_db():
    db = {}
    try:
        with open('db.json') as f:
            db = json.load(f)
    except FileNotFoundError:
        click.echo('Creating db.json...')
    return db


def write_db(data):
    with open('db.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def ping(host):
    command = ['ping', '-c', '1', host]
    return subprocess.run(command, capture_output=True).returncode


def webhook_post(msg, death):
    webhook = DiscordWebhook(
        url=WEBHOOK_URL, rate_limit_retry=True)

    color = '33ff00'
    title = 'Host back online ❤️‍🩹'
    if death:
        color = 'ff0606'
        title = 'Host cannot be reached ☠️'
    embed = DiscordEmbed(title=title, description=msg, color=color)
    webhook.add_embed(embed)
    response = webhook.execute()

    if response.ok:
        click.echo('Webhook message sent successfully')
    else:
        click.secho(f'Failed to send message: {
                    response.status_code}', fg='red')


def host_death(host, info):
    msg = (f'{host}{f' ({info['nickname']})' if info['nickname'] else ''} cannot be reached'
           f'\nLast online: {info['last-alive']
                             if info['last-alive'] else 'Never'}'
           )
    webhook_post(msg, death=True)


def host_rebirth(host, info):
    msg = f'{host}{
        f' ({info['nickname']})' if info['nickname'] else ''} is now online'
    webhook_post(msg, death=False)


@click.group()
def cli():
    global WEBHOOK_URL
    WEBHOOK_URL = os.environ.get('HEALTH_CHECK_WEBHOOK')
    if WEBHOOK_URL is None:
        click.secho(
            "WARNING: $HEALTH_CHECK_WEBHOOK environment variable is not set", fg='yellow')


@cli.command()
def check():
    data = read_db()

    if len(data) == 0:
        click.echo("Watchlist is empty")
        return

    # Health-check all hosts
    click.echo('Starting health check')
    for host, info in data.items():
        click.echo(f'Checking {host}...', nl=False)

        was_alive = info['alive']
        now = datetime.now()

        if ping(host) == 0:
            click.secho(' online', fg='green')
            if not was_alive:
                host_rebirth(host, info)
            info['alive'] = True
            info['last-alive'] = now.strftime(TIME_FMT)
        else:
            click.secho(' offline', fg='red')
            if was_alive:
                host_death(host, info)
            info['alive'] = False
    click.echo('Done.')

    write_db(data)


@cli.command()
def list():
    data = read_db()

    if len(data) == 0:
        click.echo("Watchlist is empty")
        return

    click.echo('Watchlist Status ==================')
    for host, info in data.items():
        hostname = host
        if info['nickname']:
            hostname += f' ({info['nickname']})'
        c = 'red'
        if info['alive']:
            c = 'green'
        click.secho(f'{hostname}', fg=c)
        click.echo(f'\tLast Alive: {info.get('last-alive', 'Never')}')


@cli.command()
@click.argument('host')
@click.argument('nickname', required=False)
def add(host, nickname):
    data = read_db()

    alive = not bool(ping(host))
    if not alive:
        click.secho(f'WARNING: Host {
                    host} is not currently online. Double check that the hostname was entered correctly', fg='yellow')

    data[host] = {
        'alive': alive,
        'last-alive': None if not alive else datetime.now().strftime(TIME_FMT),
        'nickname': nickname
    }

    click.echo(f'Created watchlist entry for {host}{
               f' ({nickname})' if nickname else ''}')

    write_db(data)


@cli.command()
@click.argument('host')
def remove(host):
    data = read_db()

    if host not in data:
        click.echo(f'ERROR: Host {host} not found in database')
        return

    del data[host]

    click.echo(f'Deleted host: {host}')

    write_db(data)


if __name__ == '__main__':
    cli()

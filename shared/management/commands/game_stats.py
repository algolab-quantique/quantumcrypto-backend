from django.core.management.base import BaseCommand
from django.db.models import Avg, Max
from django.utils.timezone import make_aware

from shared.models import GameStatistic
from datetime import datetime


class Command(BaseCommand):
    help = "Retrieve game statistics"

    def add_arguments(self, parser):
        parser.add_argument('--protocol', type=str, help='Filter by protocol type (e.g., bb84, e91)')
        parser.add_argument('--start-date', type=str, help='Start date (YYYY-MM-DD)')
        parser.add_argument('--end-date', type=str, help='End date (YYYY-MM-DD)')
        parser.add_argument('--stat', type=str, choices=['count', 'avg_players', 'max_players', 'ip_list'],
                            help='Statistic to calculate: count, avg_players, max_players, ip_list')

    def handle(self, *args, **options):
        protocol = options['protocol']
        start_date = options['start_date']
        end_date = options['end_date']
        stat = options['stat']

        if start_date:
            start_date = make_aware(datetime.strptime(start_date, '%Y-%m-%d'))
        if end_date:
            end_date = make_aware(datetime.strptime(end_date, '%Y-%m-%d'))

        games = GameStatistic.objects.all()
        if protocol:
            games = games.filter(protocol_type=protocol)
        if start_date:
            games = games.filter(created_at__gte=start_date)
        if end_date:
            games = games.filter(created_at__lte=end_date)

        if stat == 'count':
            self.stdout.write(f"Total games: {games.count()}")
        elif stat == 'avg_players':
            avg_players = games.aggregate(avg_players=Avg('players_count'))['avg_players']
            self.stdout.write(f"Average players per game: {avg_players:.2f}" if avg_players else "No data available.")
        elif stat == 'max_players':
            max_players = games.aggregate(max_players=Max('players_count'))['max_players']
            self.stdout.write(f"Maximum players in a game: {max_players}" if max_players else "No data available.")
        elif stat == 'ip_list':
            ip_list = games.values_list('ip_address', flat=True).distinct()
            self.stdout.write("List of IP addresses:")
            for ip in ip_list:
                self.stdout.write(f" - {ip}")
        else:
            self.stdout.write("Invalid statistic requested.")

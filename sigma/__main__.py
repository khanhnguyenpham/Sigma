"""One discoverable CLI for production, demonstrations and independent checks."""
import argparse
import runpy
import sys

COMMANDS = {
    'weekly': 'sigma.forecasting.weekly',
    'stock': 'sigma.inventory.snapshot',
    'policy': 'sigma.inventory.policy',
    'delivery': 'sigma.delivery.customer',
    'refresh': 'sigma.jobs.refresh',
    'compare': 'sigma.analysis.comparison',
    'demo': 'sigma.demo',
    'release-check': 'sigma.release',
    'check-product': 'sigma.verification.product',
    'verify-refactor': 'sigma.verification.refactor',
    **{name: 'sigma.verification.' + name.removeprefix('verify-').replace('-', '_')
       for name in ['verify-weekly', 'verify-weekly-calibration', 'verify-weekly-combine',
                    'verify-weekly-local', 'verify-weekly-mix', 'verify-weekly-policy',
                    'verify-weekly-inventory', 'verify-delivery']},
    'validate-daily': 'sigma.experiments.validation',
    'calibrate-daily': 'sigma.experiments.calibration',
    'validate-seasonal-weekly': 'sigma.experiments.seasonal_weekly',
    'verify-seasonal-weekly': 'sigma.verification.seasonal_weekly',
}


def main():
    parser = argparse.ArgumentParser(description=__doc__, usage='python -m sigma COMMAND [options]')
    parser.add_argument('command', choices=COMMANDS)
    args = parser.parse_args(sys.argv[1:2])
    sys.argv = ['python -m sigma ' + args.command, *sys.argv[2:]]
    if args.command == 'weekly' and not any(arg == '--config' or arg.startswith('--config=') for arg in sys.argv[1:]):
        sys.argv.extend(['--config', 'configs/weekly.json'])
    runpy.run_module(COMMANDS[args.command], run_name='__main__')


if __name__ == '__main__':
    main()

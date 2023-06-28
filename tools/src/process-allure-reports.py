import os
import re
import subprocess
import logging
import argparse
from allure_combine import combine_allure

COMBINE_DIR = "combine"
PUT_TIMEOUT = 600



def setup_logging():
    """Initialize logging with level INFO."""
    logging.basicConfig(level=logging.INFO)


def parse_args():
    parser = argparse.ArgumentParser(description="Process allure reports")
    parser.add_argument('--operation', required=True, type=str, help='Operation type: "get" or "put"')
    parser.add_argument('--neofs_node', required=True, type=str, help='NeoFS node')
    parser.add_argument('--wallet', required=True, type=str, help='Path to the wallet')
    parser.add_argument('--cid', required=True, type=str, help='Container ID')
    parser.add_argument('--run_number', required=True, type=int, help='GitHub run number')
    parser.add_argument('--allure_report', type=str, help='Path to allure result directory', default='allure-results')
    return parser.parse_args()


def put_report(directory: str, neofs_node: str, wallet: str, cid: str, run_number: int, password: str) -> None:
    html_file_name = 'test-report.html'
    for subdir, dirs, files in os.walk(directory):
        for filename in files:
            filepath = subdir + os.sep + filename
            filepath_send = re.sub(r'^\.', '', filepath)

            logging.debug(f'{filepath} - {filepath_send}')

            object_cmd = (
                f'NEOFS_CLI_PASSWORD={password} neofs-cli --rpc-endpoint {neofs_node}:8080 --wallet {wallet} '
                f'object put --cid {cid} --file {filepath} --attributes FilePath={run_number}/{html_file_name} RunNumber={run_number} --timeout {PUT_TIMEOUT}s'
            )

            logging.debug(f'Cmd: {object_cmd}')

            try:
                compl_proc = subprocess.run(object_cmd, check=True, universal_newlines=True,
                                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=PUT_TIMEOUT,
                                            shell=True)

                logging.debug(f'Output: {compl_proc.stdout}')

            except subprocess.CalledProcessError as e:
                raise Exception(
                    "command '{}' return with error (code {}): {}".format(e.cmd, e.returncode, e.output))


def get_history(directory: str, neofs_node: str, private_key: str, cid: str):
    pass


def process_allure_reports(operation: str, allure_path: str, neofs_node: str, wallet: str, cid: str, run_number: int,
                           neofs_password: str) -> None:
    if operation == 'get':
        get_history()
    elif operation == 'put':
        put_report(allure_path, neofs_node, wallet, cid, run_number, neofs_password)  # Uploading report
    else:
        logging.error('Invalid operation! Use "get" or "put".')


def combine_report(allure_path: str) -> str:
    combine_dir = os.path.join(os.getcwd(), COMBINE_DIR)
    os.makedirs(combine_dir, exist_ok=True)

    combine_allure(
        allure_path,
        dest_folder=combine_dir,
        auto_create_folders=True,
        remove_temp_files=True,
        ignore_utf8_errors=True,
    )

    return combine_dir


def get_password() -> str:
    password = os.getenv('NEOFS_PASSWORD')
    return password


if __name__ == '__main__':
    setup_logging()
    args = parse_args()
    result_path = combine_report(args.allure_report)
    neofs_password = get_password()
    process_allure_reports(args.operation, result_path, args.neofs_node, args.wallet, args.cid, args.run_number, neofs_password)

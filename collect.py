import json
import os
import sys
import argparse

import constants
from collector import get_category_urls
from helpers import function_entry, pe
from helpers.errors import save_to_disk
from helpers.futures import interrupt_futures
from collector.get_function_data import get_function_data
from collector.get_functions import get_functions_by_header_entry, get_functions_by_technology_entry
from tqdm import tqdm
import concurrent.futures

CATALOG_PATH = os.path.join(constants.ROOT_PATH, "catalog.json")


def stage1(*, args):
    stopped = False
    all_function_entries = []
    try:
        if args.reset_cached_catalog:
            # Assume the file is not found, which forces the script to start from scratch.
            raise FileNotFoundError
        with open(CATALOG_PATH, "r") as f:
            # Without forcing a catalog reset, the function still reads the catalog so that new entries
            # can be appended for cached runs.
            all_function_entries = json.load(f)
        if not args.use_cached_catalog:
            # If the cache is not used, scan as normal, but append instead.
            raise FileNotFoundError
    except (FileNotFoundError, json.JSONDecodeError):
        category_urls = get_category_urls.get_category_urls()
        futures = []
        with concurrent.futures.ThreadPoolExecutor(args.parallel_threads) as executor:
            if len(args.headers) > 0:
                for category in category_urls["headers"]:
                    if args.headers.count(category["header"].lower()) > 0:
                        futures.append(executor.submit(
                            get_functions_by_header_entry, category
                        ))
            else:
                for category in category_urls["technologies"]:
                    futures.append(executor.submit(
                        get_functions_by_technology_entry, category
                    ))
                for category in category_urls["headers"]:
                    futures.append(executor.submit(
                        get_functions_by_header_entry, category
                    ))

            with tqdm(total=len(futures)) as progress_bar:
                with interrupt_futures(futures):
                    for future in concurrent.futures.as_completed(futures):
                        try:
                            function_entries = future.result()
                            for entry in function_entries:
                                all_function_entries.append(entry)
                            progress_bar.update(1)
                        except KeyboardInterrupt as e:
                            stopped = True
                        except concurrent.futures.InvalidStateError:
                            stopped = True
                        except Exception as e:
                            if args.ignore_catalog_errors:
                                raise e
                            else:
                                save_to_disk(e)

        if stopped:
            sys.exit(1)

    all_function_entries = function_entry.deduplicate_entries(all_function_entries)

    with open(CATALOG_PATH, "w") as f:
        json.dump(all_function_entries, f, indent=2)

    for static_dir in args.static_dirs:
        for root, _, files in os.walk(static_dir):
            for file in files:
                path = os.path.join(root, file)
                try:
                    with open(path, 'r') as f:
                        data = json.load(f)
                        for entry in data:
                            entry["static"] = True
                            all_function_entries.append(entry)
                except (FileNotFoundError, json.decoder.JSONDecodeError):
                    print(f"Static file {path} cannot be read.", file=sys.stderr)

    all_function_entries = function_entry.deduplicate_entries(all_function_entries)

    return all_function_entries


def stage2(function_entries, *, args):
    stopped = False
    with concurrent.futures.ThreadPoolExecutor(args.parallel_threads) as executor:
        futures = []

        for entry in function_entries:
            should_process = function_entry.should_process_entry(entry, args)
            if should_process:
                futures.append(executor.submit(
                    get_function_data, entry
                ))

        with tqdm(total=len(futures)) as progress_bar:
            with interrupt_futures(futures):
                for future in concurrent.futures.as_completed(futures):
                    try:
                        result = future.result()
                        function_entry.save_entry(result)
                    except KeyboardInterrupt as e:
                        stopped = True
                    except concurrent.futures.InvalidStateError:
                        stopped = True
                    except Exception as e:
                        save_to_disk(e)
                    progress_bar.update(1)

    if stopped:
        sys.exit(1)


def main():
    pass

    available_cores = os.cpu_count()

    parser = argparse.ArgumentParser()
    parser.add_argument("--disable-cache", dest="cached", action="store_false", default=True,
                        help="Disable caching and process all entries.")
    parser.add_argument("--ignore-catalog-errors", dest="ignore_catalog_errors", action="store_true", default=False,
                        help="Prevent fatal exit on errors during catalog collection.")
    g2 = parser.add_mutually_exclusive_group()
    g2.add_argument("--use-cached-catalog", dest="use_cached_catalog", action="store_true", default=False,
                    help="Use cached version of catalog.")
    g2.add_argument("--reset-cached-catalog", dest="reset_cached_catalog", action="store_true", default=False,
                    help="Reset catalog and scrape without a cache.")
    parser.add_argument("--parallel-threads",
                        dest="parallel_threads",
                        action="store_true",
                        default=available_cores // 2,
                        help="Parallel threads.")
    parser.add_argument("--static", dest="static_dirs", action="append",
                        default=[],
                        help="Add static directories to process. Useful in documentation pages without "
                             "common formats.")
    parser.add_argument("--static-only", dest="static_only", action="store_true", default=False,
                        help="Only parse user-supplied static entries.")
    g1 = parser.add_mutually_exclusive_group()
    g1.add_argument("--header",
                    dest="headers",
                    action="append",
                    default=[],
                    help="Headers to force process. Otherwise skip. If empty, will process all unprocessed entries.")
    g1.add_argument("-f", "--specific-function", dest="specific_functions",
                    action="append",
                    default=[],
                    help="Process specific functions only.")
    g1.add_argument("-e", "--executable", dest="executable",
                    help="Process specific functions from an executable only.")
    args = parser.parse_args()

    if args.cached:
        print("Entry caching is enabled.")
    else:
        print("Entry caching is disabled.")

    os.makedirs(os.path.join(constants.ROOT_PATH, "database"), exist_ok=True)

    for i, header in enumerate(args.headers):
        if header:
            args.headers[i] = header.lower()

    if args.executable is not None:
        args.specific_functions = []
        for _import in pe.analyze_imports(args.executable):
            args.specific_functions.append(_import["name"])

    all_function_entries = stage1(args=args)
    stage2(all_function_entries, args=args)

    sys.exit(0)


if __name__ == '__main__':
    main()

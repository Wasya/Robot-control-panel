#!/usr/bin/env python3
"""Module for parsing Robot Framework files and running tests."""
import os
import sys
import subprocess
import shlex
from robot.api import get_model
from robot import run as robot_run


class RealTimeListener:
    """
    Custom Robot Framework Listener (API V2) to capture real-time events.
    Sends logs, test start, and test end events back to the GUI thread.
    """
    ROBOT_LISTENER_API_VERSION = 2

    def __init__(self, callback):
        self.callback = callback

    def start_test(self, name, attrs):
        self.callback("start_test", f"START: {name}", attrs)

    def end_test(self, name, attrs):
        status = attrs['status']
        self.callback("end_test", f"END: {name} [{status}]", attrs)

    def log_message(self, message):
        msg_str = f"[{message['level']}] {message['message']}"
        self.callback("log", msg_str, None)


def parse_robot_file(file_path):
    """
    Parses a Robot Framework file and returns a list of test cases and unique tags.
    """
    try:
        model = get_model(file_path)
        test_cases_data = []
        all_tags = set()

        for section in model.sections:
            if hasattr(section, "header") and section.header and section.header.name == "Test Cases":
                for test_case in section.body:
                    if not hasattr(test_case, "name") or not test_case.name:
                        continue
                    doc = ""
                    tags = []
                    for item in test_case.body:
                        if hasattr(item, "type"):
                            if item.type == "DOCUMENTATION":
                                # Extract documentation string
                                doc = " ".join(token.value for token in item.tokens if token.type == "ARGUMENT")
                            elif item.type == "TAGS":
                                # Extract tags and add to set
                                current_tags = [token.value for token in item.tokens if token.type == "ARGUMENT"]
                                tags.extend(current_tags)
                                all_tags.update(current_tags)
                    test_cases_data.append({
                        "name": test_case.name,
                        "documentation": doc,
                        "tags": tags
                    })
        return test_cases_data, sorted(list(all_tags))
    except Exception as e:
        print(f"Error parsing file {file_path}: {e}")
        return [], []


def get_environment_info():
    """Gathers information about the Python and Robot Framework environment."""
    info = {
        "python_version": sys.version.split()[0],
        "executable": sys.executable,
        "robot_version": "Unknown",
        "libraries": []
    }
    try:
        import robot
        info["robot_version"] = robot.__version__
    except ImportError:
        pass

    # Use pip list to find relevant libraries like Selenium, Requests, etc.
    try:
        result = subprocess.run([sys.executable, "-m", "pip", "list"], capture_output=True, text=True)
        lines = result.stdout.splitlines()
        for line in lines:
            if any(x in line.lower() for x in ["robotframework", "selenium", "requests"]):
                parts = line.split()
                if len(parts) >= 2: info["libraries"].append((parts[0], parts[1]))
    except Exception:
        pass
    return info


def run_tests_api(file_path, test_cases, tags, runs, options, callback):
    """
    Executes Robot Framework tests using the robot.run API.
    Handles run options, arguments, and variable injection.
    """

    # Base options for robot.run
    robot_options = {
        "outputdir": options.get("outputdir", "results"),
        "log": "log.html",
        "report": "report.html",
        "stdout": None,
        "stderr": None,
        "dryrun": options.get("dryrun", False),
        # loglevel is only set if provided (not the empty string ' ')
        "loglevel": options.get("loglevel"),
        "exitonfailure": options.get("exitonfailure", False),
    }

    if test_cases:
        robot_options["test"] = test_cases

    includes = tags if tags else []

    variables = options.get("variables_list", [])

    # Process additional CLI arguments entered by the user
    extra_args_str = options.get("additional_args", "").strip()
    if extra_args_str:
        try:
            tokens = shlex.split(extra_args_str)
            i = 0
            while i < len(tokens):
                key = tokens[i]
                val = tokens[i + 1] if i + 1 < len(tokens) else None

                # Handling common arguments manually to integrate with API options
                if key in ['-v', '--variable'] and val:
                    variables.append(val)
                    i += 2
                elif key in ['-i', '--include'] and val:
                    includes.append(val)
                    i += 2
                elif key in ['-e', '--exclude'] and val:
                    if "exclude" not in robot_options: robot_options["exclude"] = []
                    robot_options["exclude"].append(val)
                    i += 2
                elif key in ['-L', '--loglevel'] and val:
                    robot_options["loglevel"] = val  # CLI argument overrides GUI selection
                    i += 2
                elif key in ['-d', '--outputdir'] and val:
                    robot_options["outputdir"] = val
                    i += 2
                elif key == '--dryrun':
                    robot_options["dryrun"] = True
                    i += 1
                elif key == '--randomize' and val:
                    robot_options["randomize"] = val
                    i += 2
                else:
                    i += 1
        except Exception as e:
            callback("log", f"[WARN] Failed to parse additional args: {e}", None)

    if variables:
        robot_options["variable"] = variables

    if includes:
        robot_options["include"] = includes

    listener = RealTimeListener(callback)
    output_dir_abs = os.path.abspath(robot_options["outputdir"])

    # === FIX FOR ATTRIBUTE ERROR (Milestone 0.2.3) ===
    # If the value of loglevel is None (from GUI default) or an empty string,
    # remove the key entirely so robot.run() uses its own default logic (INFO).
    loglevel_val = robot_options.get("loglevel")
    if loglevel_val is None or (isinstance(loglevel_val, str) and loglevel_val.strip() == ""):
        if "loglevel" in robot_options:
            del robot_options["loglevel"]
    # =================================================

    for i in range(runs):
        callback("info", f"--- Run {i + 1}/{runs} ---", None)
        try:
            robot_run(file_path, listener=listener, **robot_options)
        except Exception as e:
            callback("error", f"Critical Error: {e}", None)

    return output_dir_abs
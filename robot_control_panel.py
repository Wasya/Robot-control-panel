#       ____        __          __     ______            __             __   ____                   __
#      / __ \____  / /_  ____  / /_   / ____/___  ____  / /__________  / /  / __ \____ _____  ___  / /
#     / /_/ / __ \/ __ \/ __ \/ __/  / /   / __ \/ __ \/ __/ ___/ __ \/ /  / /_/ / __ `/ __ \/ _ \/ / 
#    / _, _/ /_/ / /_/ / /_/ / /_   / /___/ /_/ / / / / /_/ /  / /_/ / /  / ____/ /_/ / / / /  __/ /  
#   /_/ |_|\____/_.___/\____/\__/   \____/\____/_/ /_/\__/_/   \____/_/  /_/    \__,_/_/ /_/\___/_/   

#!/usr/bin/env python3
import sys
import os
import json
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QCheckBox, QPushButton, QLabel,
                             QSpinBox, QFileDialog, QScrollArea, QGroupBox,
                             QMessageBox, QTextBrowser, QComboBox, QTabWidget,
                             QSplitter, QTreeWidget, QTreeWidgetItem, QTableWidget,
                             QTableWidgetItem, QHeaderView, QLineEdit, QDialog,
                             QFormLayout)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QUrl
from PyQt5.QtGui import QColor, QFont, QDesktopServices, QIcon

# Assuming the helper module is named robot_core.py
from robot_core import parse_robot_file, run_tests_api, get_environment_info


# === Class for adding a new variable dialog ===
class AddVariableDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add External Variable")
        self.setWindowTitle("Add External Variable")
        self.setGeometry(300, 300, 400, 300)
        self.layout = QFormLayout(self)

        self.name_edit = QLineEdit()
        self.type_combo = QComboBox()
        self.type_combo.addItems(["String", "Integer", "Boolean", "Choice", "Password"])
        self.type_combo.currentTextChanged.connect(self.on_type_changed)

        self.desc_edit = QLineEdit()
        self.desc_edit.setPlaceholderText("Optional description")

        self.value_edit = QLineEdit()

        self.options_edit = QLineEdit()
        self.options_edit.setPlaceholderText("Option1, Option2, Option3")
        self.options_label = QLabel("Options (comma separated):")

        self.layout.addRow("Variable Name:", self.name_edit)
        self.layout.addRow("Type:", self.type_combo)
        self.layout.addRow("Description:", self.desc_edit)
        self.layout.addRow("Default Value:", self.value_edit)
        self.layout.addRow(self.options_label, self.options_edit)

        self.buttons = QHBoxLayout()
        self.btn_add = QPushButton("Add")
        self.btn_add.clicked.connect(self.accept)
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.reject)
        self.buttons.addWidget(self.btn_add)
        self.buttons.addWidget(self.btn_cancel)
        self.layout.addRow(self.buttons)

        self.on_type_changed("String")

    def on_type_changed(self, type_text):
        is_choice = type_text == "Choice"
        self.options_edit.setVisible(is_choice)
        self.options_label.setVisible(is_choice)

        if type_text == "Boolean":
            self.value_edit.setPlaceholderText("True or False")
        else:
            self.value_edit.setPlaceholderText("")

    def get_data(self):
        return {
            "name": self.name_edit.text().strip(),
            "type": self.type_combo.currentText().lower(),
            "description": self.desc_edit.text().strip(),
            "default": self.value_edit.text().strip(),
            "value": self.value_edit.text().strip(),
            "options": [opt.strip() for opt in self.options_edit.text().split(",") if opt.strip()]
        }


class TestRunnerThread(QThread):
    # Signals for real-time logging and completion status
    log_signal = pyqtSignal(str, str, object)
    finished_signal = pyqtSignal(str)

    def __init__(self, file_path, test_cases, tags, runs, options):
        super().__init__()
        self.file_path = file_path
        self.test_cases = test_cases
        self.tags = tags
        self.runs = runs
        self.options = options

    def run(self):
        # Calls the core robot execution function
        output_dir = run_tests_api(
            self.file_path, self.test_cases, self.tags,
            self.runs, self.options, self.emit_log
        )
        self.finished_signal.emit(output_dir)

    def emit_log(self, msg_type, message, payload):
        self.log_signal.emit(msg_type, message, payload)


class RobotControlPanel(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Robot Framework Control Panel v0.2.2")
        self.setGeometry(100, 100, 1200, 900)

        self.current_file = None
        self.test_cases = []
        self.all_tags = []
        self.test_checkboxes = []
        self.tag_checkboxes = []

        # Configuration file paths
        self.config_file = os.path.join(os.path.expanduser("~"), ".robot_control_panel.json")
        self.vars_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "robot_variables.json")

        self.param_history = []
        self.external_variables = []
        self.var_widgets = {}  # Stores references to dynamic variable widgets

        self.init_ui()
        self.load_config()
        self.load_variables()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # File selection area
        file_layout = QHBoxLayout()
        self.file_path_label = QLabel("No file selected")
        self.file_path_label.setStyleSheet("font-weight: bold; color: #333;")
        select_file_button = QPushButton("Select .robot file")
        select_file_button.clicked.connect(self.select_file)
        file_layout.addWidget(self.file_path_label, 1)
        file_layout.addWidget(select_file_button)
        main_layout.addLayout(file_layout)

        # Tab widget for Runner, Settings, Environment
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        self.setup_runner_tab()
        self.setup_settings_tab()
        self.setup_env_tab()

        # Run button area
        action_layout = QHBoxLayout()
        self.run_button = QPushButton("Run Selected Tests")
        self.run_button.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 10px;")
        self.run_button.clicked.connect(self.run_tests)
        action_layout.addWidget(self.run_button)
        main_layout.addLayout(action_layout)

        # Report links area
        self.report_links_layout = QHBoxLayout()
        self.log_btn = QPushButton("Open Log.html")
        self.report_btn = QPushButton("Open Report.html")
        self.log_btn.clicked.connect(lambda: self.open_report("log.html"))
        self.report_btn.clicked.connect(lambda: self.open_report("report.html"))
        self.log_btn.setVisible(False)
        self.report_btn.setVisible(False)
        self.report_links_layout.addWidget(self.log_btn)
        self.report_links_layout.addWidget(self.report_btn)
        main_layout.addLayout(self.report_links_layout)
        self.last_output_dir = ""

    def setup_runner_tab(self):
        # Set up the main runner tab with test selection and results viewer
        runner_tab = QWidget()
        layout = QVBoxLayout(runner_tab)
        splitter = QSplitter(Qt.Horizontal)

        selection_tabs = QTabWidget()

        # Test Case Selection Panel
        tc_widget = QWidget()
        tc_layout = QVBoxLayout(tc_widget)
        self.tests_layout = QVBoxLayout()
        tc_scroll = QScrollArea()
        tc_group = QGroupBox("Test Cases")
        tc_group.setLayout(self.tests_layout)
        tc_scroll.setWidget(tc_group)
        tc_scroll.setWidgetResizable(True)
        tc_layout.addWidget(tc_scroll)

        # Test Case Selection Buttons
        tc_btns = QHBoxLayout()
        btn_all = QPushButton("All")
        btn_all.clicked.connect(self.select_all_tests)
        btn_none = QPushButton("None")
        btn_none.clicked.connect(self.deselect_all_tests)
        tc_btns.addWidget(btn_all)
        tc_btns.addWidget(btn_none)
        tc_layout.addLayout(tc_btns)

        # Tag Selection Panel
        tag_widget = QWidget()
        tag_layout = QVBoxLayout(tag_widget)
        self.tags_layout = QVBoxLayout()
        tag_scroll = QScrollArea()
        tag_group = QGroupBox("Tags")
        tag_group.setLayout(self.tags_layout)
        tag_scroll.setWidget(tag_group)
        tag_scroll.setWidgetResizable(True)
        tag_layout.addWidget(tag_scroll)

        selection_tabs.addTab(tc_widget, "Test Cases")
        selection_tabs.addTab(tag_widget, "Tags")
        splitter.addWidget(selection_tabs)

        # Results Viewer Panel
        results_widget = QWidget()
        results_layout = QVBoxLayout(results_widget)
        self.results_tree = QTreeWidget()
        self.results_tree.setHeaderLabels(["Test Case", "Status", "Duration/Msg"])
        self.results_tree.setColumnWidth(0, 350)
        results_layout.addWidget(self.results_tree, 1)
        self.results_text = QTextBrowser()
        self.results_text.setFont(QFont("Consolas", 9))
        results_layout.addWidget(self.results_text, 1)
        splitter.addWidget(results_widget)
        splitter.setSizes([400, 800])  # Initial split sizes

        layout.addWidget(splitter)
        self.tabs.addTab(runner_tab, "Runner")

    def setup_settings_tab(self):
        # Set up the run configuration and external variables tab
        settings_tab = QWidget()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)
        scroll.setWidget(content_widget)

        group_base = QGroupBox("Run Configuration")
        form_base = QVBoxLayout()

        self.chk_dryrun = QCheckBox("Dry Run (Validate tests without execution)")
        self.chk_exitonfail = QCheckBox("Exit on first failure")

        # Number of runs
        hbox_runs = QHBoxLayout()
        hbox_runs.addWidget(QLabel("Number of Runs:"))
        self.runs_spin = QSpinBox()
        self.runs_spin.setRange(1, 100)
        hbox_runs.addWidget(self.runs_spin)
        hbox_runs.addStretch()

        # Log Level combo box
        hbox_log = QHBoxLayout()
        hbox_log.addWidget(QLabel("Log Level:"))
        self.combo_loglevel = QComboBox()

        # MILESTONE 0.2.2: Add empty string as default to use CLI default behavior
        self.combo_loglevel.addItems([" ", "INFO", "DEBUG", "TRACE", "WARN"])
        self.combo_loglevel.setCurrentText(" ")

        hbox_log.addWidget(self.combo_loglevel)
        hbox_log.addStretch()

        # Output directory
        hbox_output = QHBoxLayout()
        self.edit_output_dir = QLineEdit("results")
        hbox_output.addWidget(QLabel("Output Directory:"))
        hbox_output.addWidget(self.edit_output_dir)

        form_base.addWidget(self.chk_dryrun)
        form_base.addWidget(self.chk_exitonfail)
        form_base.addLayout(hbox_runs)
        form_base.addLayout(hbox_log)
        form_base.addLayout(hbox_output)
        group_base.setLayout(form_base)
        layout.addWidget(group_base)

        # External Variables Group
        group_vars = QGroupBox("External Variables")
        vars_layout = QVBoxLayout()

        self.vars_table = QTableWidget()
        self.vars_table.setColumnCount(3)
        self.vars_table.setHorizontalHeaderLabels(["Variable Info", "Value Control", "Action"])
        self.vars_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.vars_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.vars_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.vars_table.setMinimumHeight(200)
        vars_layout.addWidget(self.vars_table)

        btn_add_var = QPushButton(" + Add Variable ")
        btn_add_var.clicked.connect(self.add_variable_dialog)
        vars_layout.addWidget(btn_add_var)

        group_vars.setLayout(vars_layout)
        layout.addWidget(group_vars)

        # CLI Arguments Group (History)
        group_cli = QGroupBox("Command Line Arguments (Advanced)")
        cli_layout = QVBoxLayout()

        params_layout = QHBoxLayout()
        self.params_combo = QComboBox()
        self.params_combo.setEditable(True)
        self.params_combo.setInsertPolicy(QComboBox.NoInsert)
        self.params_combo.currentTextChanged.connect(self.on_params_changed)
        params_layout.addWidget(self.params_combo, 1)

        delete_param_button = QPushButton("Delete")
        delete_param_button.clicked.connect(self.delete_param)
        params_layout.addWidget(delete_param_button)

        cli_layout.addLayout(params_layout)
        cli_layout.addWidget(QLabel("<small><i>Example: --randomize all --listener MyListener.py</i></small>"))
        group_cli.setLayout(cli_layout)
        layout.addWidget(group_cli)

        layout.addStretch()

        tab_main_layout = QVBoxLayout(settings_tab)
        tab_main_layout.addWidget(scroll)

        self.tabs.addTab(settings_tab, "Run Settings")

    def setup_env_tab(self):
        # Set up the environment information tab
        env_tab = QWidget()
        layout = QVBoxLayout(env_tab)
        btn_refresh = QPushButton("Refresh Environment Info")
        btn_refresh.clicked.connect(self.refresh_env_info)
        layout.addWidget(btn_refresh)
        self.env_table = QTableWidget()
        self.env_table.setColumnCount(2)
        self.env_table.setHorizontalHeaderLabels(["Component", "Version/Path"])
        self.env_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.env_table)
        self.tabs.addTab(env_tab, "Environment")
        self.refresh_env_info()

    # === Variable Management Logic ===

    def load_variables(self):
        # Load external variables from JSON file
        if os.path.exists(self.vars_file):
            try:
                with open(self.vars_file, "r", encoding="utf-8") as f:
                    self.external_variables = json.load(f)
            except Exception as e:
                print(f"Error loading vars: {e}")
        else:
            # Create a default variable if file doesn't exist
            self.external_variables = [{
                "name": "HEADLESS",
                "type": "boolean",
                "default": "True",
                "description": "Run browser in headless mode",
                "value": "True"
            }]
            self.save_variables()

        self.render_variables()

    def save_variables(self):
        # Update variable values from UI before saving
        self.update_variable_values_from_ui()
        try:
            with open(self.vars_file, "w", encoding="utf-8") as f:
                json.dump(self.external_variables, f, indent=2)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to save variables: {e}")

    def update_variable_values_from_ui(self):
        # Read current values from the dynamic widgets
        for var in self.external_variables:
            name = var["name"]
            widget = self.var_widgets.get(name)
            if widget:
                val = ""
                vtype = var["type"]

                if vtype == "boolean":
                    val = str(widget.isChecked())
                elif vtype == "integer":
                    val = str(widget.value())
                elif vtype == "choice":
                    val = widget.currentText()
                elif vtype == "string" or vtype == "password":
                    val = widget.text()

                var["value"] = val

    def render_variables(self):
        # Render the variable table based on self.external_variables
        self.vars_table.setRowCount(0)
        self.var_widgets = {}

        for row, var in enumerate(self.external_variables):
            self.vars_table.insertRow(row)

            # Column 0: Variable Info
            name_item = QTableWidgetItem(var["name"])
            name_item.setFlags(Qt.ItemIsEnabled)
            if var.get("description"):
                name_item.setToolTip(var["description"])
                name_item.setIcon(QIcon.fromTheme("help-about"))
            self.vars_table.setItem(row, 0, name_item)

            # Column 1: Value Control Widget (Checkbox, SpinBox, LineEdit, etc.)
            control_widget = self.create_control_for_var(var)
            self.var_widgets[var["name"]] = control_widget
            self.vars_table.setCellWidget(row, 1, control_widget)

            # Column 2: Delete Button
            btn_del = QPushButton("X")
            btn_del.setFixedSize(30, 25)
            btn_del.setStyleSheet("color: red; font-weight: bold;")
            btn_del.clicked.connect(lambda checked, r=row: self.delete_variable(r))

            cell_widget = QWidget()
            layout = QHBoxLayout(cell_widget)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setAlignment(Qt.AlignCenter)
            layout.addWidget(btn_del)
            self.vars_table.setCellWidget(row, 2, cell_widget)

    def create_control_for_var(self, var):
        # Factory function to create appropriate widget based on variable type
        vtype = var["type"]
        default_val = var.get("value", var.get("default", ""))

        if vtype == "boolean":
            widget = QCheckBox()
            widget.setChecked(default_val.lower() == "true")
            return widget

        elif vtype == "integer":
            widget = QSpinBox()
            widget.setRange(-999999, 999999)
            try:
                widget.setValue(int(default_val))
            except Exception as e:
                widget.setValue(0)
                print(f"Error loading vars: {e}")
            return widget

        elif vtype == "choice":
            widget = QComboBox()
            options = var.get("options", [])
            widget.addItems(options)
            widget.setCurrentText(default_val)
            return widget

        elif vtype == "password":
            widget = QLineEdit()
            widget.setEchoMode(QLineEdit.Password)
            widget.setText(default_val)
            return widget

        else:  # Default is String
            widget = QLineEdit()
            widget.setText(default_val)
            return widget

    def add_variable_dialog(self):
        # Open dialog to add a new variable
        dialog = AddVariableDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            if not data["name"]:
                QMessageBox.warning(self, "Error", "Variable name is required!")
                return

            for v in self.external_variables:
                if v["name"] == data["name"]:
                    QMessageBox.warning(self, "Error", "Variable already exists!")
                    return

            self.external_variables.append(data)
            self.save_variables()
            self.render_variables()

    def delete_variable(self, row_index):
        # Delete a variable from the list
        if 0 <= row_index < len(self.external_variables):
            name = self.external_variables[row_index]["name"]
            reply = QMessageBox.question(self, 'Delete Variable',
                                         f"Delete variable '{name}'?",
                                         QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.Yes:
                del self.external_variables[row_index]
                self.save_variables()
                self.render_variables()

    # === Standard Logic (File, Env, Run) ===

    def refresh_env_info(self):
        # Get and display system and Robot Framework environment info
        info = get_environment_info()
        rows = [("Python", info["python_version"]), ("Robot Framework", info["robot_version"])] + info["libraries"]
        self.env_table.setRowCount(len(rows))
        for i, (k, v) in enumerate(rows):
            self.env_table.setItem(i, 0, QTableWidgetItem(k))
            self.env_table.setItem(i, 1, QTableWidgetItem(v))

    def select_file(self):
        # Open file dialog and load test cases upon selection
        fp, _ = QFileDialog.getOpenFileName(self, "Select Robot File", "", "Robot Files (*.robot)")
        if fp:
            self.current_file = fp
            self.file_path_label.setText(fp)
            self.load_test_cases(fp)

    def load_test_cases(self, fp):
        # Parse file and populate the test case and tag checkboxes
        for cb in self.test_checkboxes + self.tag_checkboxes:
            cb.deleteLater()
        self.test_checkboxes, self.tag_checkboxes = [], []
        self.test_cases, self.all_tags = parse_robot_file(fp)
        for tc in self.test_cases:
            cb = QCheckBox(tc["name"])
            if tc["documentation"]:
                cb.setToolTip(tc["documentation"])
            self.tests_layout.addWidget(cb)
            self.test_checkboxes.append(cb)
        for tag in self.all_tags:
            cb = QCheckBox(tag)
            self.tags_layout.addWidget(cb)
            self.tag_checkboxes.append(cb)

    def select_all_tests(self):
        for cb in self.test_checkboxes:
            cb.setChecked(True)

    def deselect_all_tests(self):
        for cb in self.test_checkboxes:
            cb.setChecked(False)

    def load_config(self):
        # Load history of additional parameters
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, "r") as f:
                    cfg = json.load(f)
                    self.param_history = cfg.get("param_history", [])
                    self.params_combo.clear()
                    self.params_combo.addItems(self.param_history)
                    self.params_combo.setCurrentText("")
        except Exception as e:
            print(f"Error load config: {e}")
            pass

    def save_config(self):
        # Save history of additional parameters
        try:
            with open(self.config_file, "w") as f:
                json.dump({"param_history": self.param_history}, f)
        except Exception as e:
            print(f"Error saving config: {e}")
            pass

    def on_params_changed(self, t):
        # Placeholder for future logic, currently just passes
        pass

    def delete_param(self):
        # Delete parameter from history
        ct = self.params_combo.currentText()
        if ct in self.param_history:
            self.param_history.remove(ct)
            self.params_combo.removeItem(self.params_combo.currentIndex())
            self.save_config()

    def run_tests(self):
        # Main test execution handler
        if not self.current_file:
            return QMessageBox.warning(self, "Error", "Select file first.")

        # Collect selected tests and tags
        sel_tests = [self.test_cases[i]["name"] for i, cb in enumerate(self.test_checkboxes) if cb.isChecked()]
        sel_tags = [self.all_tags[i] for i, cb in enumerate(self.tag_checkboxes) if cb.isChecked()]
        if not sel_tests and not sel_tags:
            return QMessageBox.warning(self, "Error", "Select test or tag.")

        # Handle additional CLI arguments history
        add_args = self.params_combo.currentText().strip()
        if add_args and add_args not in self.param_history:
            self.param_history.insert(0, add_args)
            self.params_combo.insertItem(0, add_args)
            self.save_config()

        # Update and save current variable values
        self.update_variable_values_from_ui()
        self.save_variables()

        # Format variables for Robot Framework CLI
        variables_list = [f"{var['name']}:{var['value']}" for var in self.external_variables]

        # UI cleanup before run
        self.run_button.setEnabled(False)
        self.run_button.setText("Running...")
        self.results_text.clear()
        self.results_tree.clear()
        self.current_tree_items = {}
        self.log_btn.setVisible(False)
        self.report_btn.setVisible(False)

        # --- MILESTONE 0.2.2: Handle empty string for default loglevel ---
        selected_loglevel = self.combo_loglevel.currentText()

        options = {
            "dryrun": self.chk_dryrun.isChecked(),
            "exitonfailure": self.chk_exitonfail.isChecked(),
            "outputdir": self.edit_output_dir.text(),
            "additional_args": add_args,
            "variables_list": variables_list
        }

        # Only pass loglevel if the selected value is not the empty string
        if selected_loglevel.strip() != "":
            options["loglevel"] = selected_loglevel
        # ----------------------------------------------------------------

        # Start the runner thread
        self.runner_thread = TestRunnerThread(self.current_file, sel_tests, sel_tags, self.runs_spin.value(), options)
        self.runner_thread.log_signal.connect(self.handle_log)
        self.runner_thread.finished_signal.connect(self.tests_finished)
        self.runner_thread.start()

    def handle_log(self, mt, msg, pl):
        # Handle real-time logs from the runner thread
        if mt == "log":
            c = "black"
            if "[WARN]" in msg:
                c = "orange"
            if "[FAIL]" in msg:
                c = "red"
            self.results_text.append(f'<span style="color:{c}">{msg}</span>')
        elif mt == "start_test":
            tn = msg.replace("START: ", "")
            item = QTreeWidgetItem(self.results_tree)
            item.setText(0, tn)
            item.setText(1, "Running...")
            item.setBackground(1, QColor("yellow"))
            self.current_tree_items[tn] = item
            self.results_tree.scrollToItem(item)
        elif mt == "end_test":
            tn = msg.split(" [")[0].replace("END: ", "")
            st = pl['status']
            if tn in self.current_tree_items:
                it = self.current_tree_items[tn]
                it.setText(1, st)
                it.setBackground(1, QColor("#ccffcc") if st == "PASS" else QColor("#ffcccc"))
                if st != "PASS":
                    it.setExpanded(True)

    def tests_finished(self, od):
        # Handler after thread completes
        self.run_button.setEnabled(True)
        self.run_button.setText("Run Selected Tests")
        self.last_output_dir = od
        self.results_text.append("\n=== Done ===")
        self.log_btn.setVisible(True)
        self.report_btn.setVisible(True)

    def open_report(self, fn):
        # Open HTML reports in the default web browser
        p = os.path.join(self.last_output_dir, fn)
        if os.path.exists(p):
            QDesktopServices.openUrl(QUrl.fromLocalFile(p))
        else:
            QMessageBox.warning(self, "Error", f"File not found: {p}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setFont(QFont("Segoe UI", 9))
    w = RobotControlPanel()
    w.show()
    sys.exit(app.exec_())

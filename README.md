# Robot Framework Control Panel (v0.2.2)

This is a cross-platform desktop application built using PyQt5 to provide a Graphical User Interface (GUI) for managing and executing Robot Framework test suites.

## ✨ Key Features

* **Test Suite Selection**: Easily select and load `.robot` files.
* **Flexible Execution**: Run tests based on specific **Test Cases** or **Tags**.
* **Run Configuration (Settings)**: Fine-tune execution parameters.
* **External Variables Management**: Control dynamic variables (e.g., `BROWSER`, `URL`) via the GUI.
* **Real-time Console**: View execution logs in a dedicated results area.
* **Environment Info**: Quick check of Python and Robot Framework library versions.

---

## ⚙️ New Features (v0.2.2)

1.  **External Variables Management**:
    * Ability to create, save, and manage **external variables** (e.g., `HEADLESS`, `BROWSER`) through the GUI.
    * Supports various types: **String, Integer, Boolean, Choice (ComboBox), Password**.
    * Variables are automatically passed to Robot Framework as `-v NAME:VALUE`.
    * Configuration is persisted in `robot_variables.json`.

2.  **Log Level Control**:
    * Added a setting for explicit log level (**TRACE, DEBUG, INFO, WARN**) in the "Run Settings" tab.
    * The default option **" "** (empty) is used to **not** pass the `--loglevel` argument to Robot Framework, preserving the default CLI behavior and log fidelity.

3.  **Advanced Run Settings**:
    * Configuration for **Output Directory**.
    * Checkboxes for **Dry Run** and **Exit on first failure**.

---

## 🚀 Getting Started

### Requirements

* Python 3.6+
* Robot Framework (`pip install robotframework`)
* PyQt5 (`pip install PyQt5`)

### Running the Application

1.  Clone the repository.
2.  Install dependencies.
3.  Launch the application:
    ```bash
    python robot_control_panel.py
    ```

### Usage Workflow

1.  Click **"Select .robot file"** to load your test suite.
2.  In the **Runner** tab, select the desired tests or tags.
3.  In the **Run Settings** tab, configure variables and execution options.
4.  Click **"Run Selected Tests"**.
5.  Check the results in the execution panel and use the **Log/Report** buttons to open the HTML reports.

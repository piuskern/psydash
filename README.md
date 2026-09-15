<h1>
  <img src="assets/icon/icon.png" width="70" align="center">
  PsyDash
</h1>
A dashboard app that helps you track and visualize progress across psychotherapy sessions.

## Installation

This project uses [uv](https://docs.astral.sh/uv/) to manage its Python version, virtual environment, and dependencies.

1. Install uv (if you don't have it already):
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

2. Clone the repository:
```bash
git clone https://github.com/piuskern/psydash.git
cd psydash
```

3. Install dependencies (uv creates `.venv` and installs the pinned Python version automatically):
```bash
uv sync
```

## Running the Application

1. Start the application:
```bash
uv run python app.py
```

2. Open your web browser and navigate to:
```
http://localhost:8050
```
## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

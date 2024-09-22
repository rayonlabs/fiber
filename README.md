# Fiber

Fiber is a lightweight, developer-friendly package for running Bittensor subnets.

Fiber is designed to be a highly secure networking framework that utilizes Multi-Layer Transport Security (MLTS) for enhanced data protection, offers DDoS resistance, and is designed to be easily extendable across multiple programming languages.

### For dev
```bash
python -m venv venv || python3 -m venv venv
source venv/bin/activate
pip install -e .
pre-commit install
```

### Run dev miner
```bash
cd dev_utils
python start_miner.py
```

### Run dev validator
```bash
cd dev_utils
python run_validator.py
```

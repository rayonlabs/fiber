# Fiber

Fiber is a lightweight, developer-friendly package for running Bittensor subnets.

Fiber is designed to be a highly secure networking framework that utilizes Multi-Layer Transport Security (MLTS) for enhanced data protection, offers DDoS resistance, and is designed to be easily extendable across multiple programming languages.


## Installation

### Install Full fiber - with all networking + chain stuff
----
```bash
pip install "git+https://github.com/rayonlabs/fiber.git@x.y.z#egg=fiber[full]"
```

Replace x.y.z with the desired version (or remove it to install the latest version)

### Install Fiber with only Chain interactions
----


```bash
pip install "git+https://github.com/rayonlabs/fiber.git@x.y.z"
```

Or:


```bash
pip install "git+https://github.com/rayonlabs/fiber.git@x.y.z#egg=fiber[chain]"
```


---

#### For dev
```bash
python -m venv venv || python3 -m venv venv
source venv/bin/activate
pip install -e .
pre-commit install
```

#### Create dev.env file for miner
```bash
WALLET_NAME=<YOUR_WALLET.NAME>
WALLET_HOTKEY=<YOUR_WALLET_HOTKEY>
```

#### Run dev miner
```bash
cd dev_utils
python start_miner.py
```

#### Create .env file for validator
```bash
WALLET_NAME=<YOUR_WALLET.NAME>
WALLET_HOTKEY=<YOUR_WALLET_HOTKEY>
NETUID=<NETUID>
SUBTENSOR_NETWORK=<NETWORK>
MIN_STAKE_THRESHOLD=<INT>
```

#### Run dev validator
```bash
cd dev_utils
python run_validator.py
```

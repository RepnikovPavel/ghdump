# Install ghdump

Requires Python 3.8+. No pip packages — stdlib only.

## Local clone

```sh
git clone https://github.com/RepnikovPavel/ghdump.git
cd ghdump
./install.sh                  # -> ~/.local/bin/ghdump (user install)
sudo ./install.sh /usr/local/bin   # -> system-wide
```

## One-line remote install (no clone)

```sh
mkdir -p ~/.local/bin && \
curl -fsSL https://raw.githubusercontent.com/RepnikovPavel/ghdump/main/dont_read_me_src/ghdump.py \
  -o ~/.local/bin/ghdump && chmod +x ~/.local/bin/ghdump
```

## Docker image

```dockerfile
RUN mkdir -p /usr/local/bin && \
    curl -fsSL https://raw.githubusercontent.com/RepnikovPavel/ghdump/main/dont_read_me_src/ghdump.py \
      -o /usr/local/bin/ghdump && chmod +x /usr/local/bin/ghdump
```

## Verify

```sh
ghdump --version
```

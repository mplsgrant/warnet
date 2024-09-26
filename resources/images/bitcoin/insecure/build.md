# Historic CVE images

These images are for old versions of Bitcoin Core with known CVEs. These images have signet backported
and the addrman and isroutable patches applied.

# Build incantations

Run from top-level of project

## v0.21.1

```bash
docker buildx build \
  --platform linux/amd64,linux/armhf \
  --build-context bitcoin-src="." \
  --build-arg ALPINE_VERSION="3.17" \
  --build-arg BITCOIN_VERSION="0.21.1" \
  --build-arg EXTRA_PACKAGES="sqlite-dev" \
  --build-arg EXTRA_RUNTIME_PACKAGES="boost-filesystem sqlite-dev" \
  --build-arg REPO="josibake/bitcoin" \
  --build-arg COMMIT_SHA="e0a22f14c15b4877ef6221f9ee2dfe510092d734" \
  --tag bitcoindevproject/bitcoin:0.21.1 \
  resources/images/bitcoin/insecure
```

## v0.20.0

```bash
docker buildx build \
  --platform linux/amd64,linux/armhf \
  --build-context bitcoin-src="." \
  --build-arg ALPINE_VERSION="3.12.12" \
  --build-arg BITCOIN_VERSION="0.20.0" \
  --build-arg EXTRA_PACKAGES="sqlite-dev miniupnpc" \
  --build-arg EXTRA_RUNTIME_PACKAGES="boost-filesystem sqlite-dev" \
  --build-arg REPO="josibake/bitcoin" \
  --build-arg COMMIT_SHA="0bbff8feff0acf1693dfe41184d9a4fd52001d3f" \
  --tag bitcoindevproject/bitcoin:0.20.0 \
  resources/images/bitcoin/insecure
```

## v0.19.2

```bash
docker buildx build \
  --platform linux/amd64,linux/armhf \
  --build-context bitcoin-src="." \
  --build-arg ALPINE_VERSION="3.12.12" \
  --build-arg BITCOIN_VERSION="0.19.2" \
  --build-arg EXTRA_PACKAGES="sqlite-dev libressl-dev" \
  --build-arg EXTRA_RUNTIME_PACKAGES="boost-chrono boost-filesystem libressl sqlite-dev" \
  --build-arg REPO="josibake/bitcoin" \
  --build-arg COMMIT_SHA="e20f83eb5466a7d68227af14a9d0cf66fb520ffc" \
  --tag bitcoindevproject/bitcoin:0.19.2 \
  resources/images/bitcoin/insecure
```

## v0.17.0

```bash
docker buildx build \
  --platform linux/amd64,linux/armhf \
  --build-context bitcoin-src="." \
  --build-arg ALPINE_VERSION="3.9" \
  --build-arg BITCOIN_VERSION="0.17.0" \
  --build-arg EXTRA_PACKAGES="protobuf-dev libressl-dev" \
  --build-arg EXTRA_RUNTIME_PACKAGES="boost boost-program_options libressl sqlite-dev" \
  --build-arg REPO="josibake/bitcoin" \
  --build-arg COMMIT_SHA="f6b2db49a707e7ad433d958aee25ce561c66521a" \
  --tag bitcoindevproject/bitcoin:0.17.0 \
  resources/images/bitcoin/insecure
```

## v0.16.1

```bash
docker buildx build \
  --platform linux/amd64,linux/armhf \
  --build-context bitcoin-src="." \
  --build-arg ALPINE_VERSION="3.7" \
  --build-arg BITCOIN_VERSION="0.16.1" \
  --build-arg EXTRA_PACKAGES="protobuf-dev libressl-dev" \
  --build-arg PRE_CONFIGURE_COMMANDS="sed -i '/AC_PREREQ/a\AR_FLAGS=cr' src/univalue/configure.ac && sed -i '/AX_PROG_CC_FOR_BUILD/a\AR_FLAGS=cr' src/secp256k1/configure.ac && sed -i 's:sys/fcntl.h:fcntl.h:' src/compat.h" \
  --build-arg EXTRA_RUNTIME_PACKAGES="boost boost-program_options libressl" \
  --build-arg REPO="josibake/bitcoin" \
  --build-arg COMMIT_SHA="dc94c00e58c60412a4e1a540abdf0b56093179e8" \
  --tag bitcoindevproject/bitcoin:0.16.1 \
  resources/images/bitcoin/insecure
```

## unknown p2p message crash

Will crash when sent an Unknown P2P message
User agent: "/unknown-message:99.1.0/"

```bash
docker buildx build \
  --platform linux/amd64,linux/armhf \
  --build-context bitcoin-src="." \
  --build-arg ALPINE_VERSION="3.20" \
  --build-arg BITCOIN_VERSION="28.1.1" \
  --build-arg EXTRA_PACKAGES="sqlite-dev" \
  --build-arg EXTRA_RUNTIME_PACKAGES="" \
  --build-arg REPO="willcl-ark/bitcoin" \
  --build-arg COMMIT_SHA="ffe3952b2ee4f66083176815fc55d092e0fcc1f8" \
  --tag bitcoindevproject/bitcoin:unknown-message \
  resources/images/bitcoin/insecure
```

## invalid blocks crash

Will crash when sent an invalid block
User agent: "/invalid-block:99.1.0/"

```bash
docker buildx build \
  --platform linux/amd64,linux/armhf \
  --build-context bitcoin-src="." \
  --build-arg ALPINE_VERSION="3.20" \
  --build-arg BITCOIN_VERSION="28.1.1" \
  --build-arg EXTRA_PACKAGES="sqlite-dev" \
  --build-arg EXTRA_RUNTIME_PACKAGES="" \
  --build-arg REPO="willcl-ark/bitcoin" \
  --build-arg COMMIT_SHA="dae4caab34b6c5c58324b1356897953c99a6e920" \
  --tag bitcoindevproject/bitcoin:invalid-blocks \
  resources/images/bitcoin/insecure
```

## too many orphans crash

Will crash when we have 50 orphans in the orphanage
User agent: "/50-orphans:99.1.0/"

```bash
docker buildx build \
  --platform linux/amd64,linux/armhf \
  --build-context bitcoin-src="." \
  --build-arg ALPINE_VERSION="3.20" \
  --build-arg BITCOIN_VERSION="28.1.1" \
  --build-arg EXTRA_PACKAGES="sqlite-dev" \
  --build-arg EXTRA_RUNTIME_PACKAGES="" \
  --build-arg REPO="willcl-ark/bitcoin" \
  --build-arg COMMIT_SHA="38aff9d695f5aa187fc3b75f08228248963372ee" \
  --tag bitcoindevproject/bitcoin:50-orphans \
  resources/images/bitcoin/insecure
```

## full mempool crash

Will crash when we would normally trim the mempool size
User agent: "/no-mp-trim:99.1.0/"

```bash
docker buildx build \
  --platform linux/amd64,linux/armhf \
  --build-context bitcoin-src="." \
  --build-arg ALPINE_VERSION="3.20" \
  --build-arg BITCOIN_VERSION="28.1.1" \
  --build-arg EXTRA_PACKAGES="sqlite-dev" \
  --build-arg EXTRA_RUNTIME_PACKAGES="" \
  --build-arg REPO="willcl-ark/bitcoin" \
  --build-arg COMMIT_SHA="f9b6fb7fdb586a57945a835fe228b9eabb137f1e" \
  --tag bitcoindevproject/bitcoin:no-mp-trim\
  resources/images/bitcoin/insecure
```

## disabled opcodes crash

Will crash when processing a disabled opcode
User agent: "/no-op-cat:99.1.0/"

```bash
docker buildx build \
  --platform linux/amd64,linux/armhf \
  --build-context bitcoin-src="." \
  --build-arg ALPINE_VERSION="3.20" \
  --build-arg BITCOIN_VERSION="28.1.1" \
  --build-arg EXTRA_PACKAGES="sqlite-dev" \
  --build-arg EXTRA_RUNTIME_PACKAGES="" \
  --build-arg REPO="willcl-ark/bitcoin" \
  --build-arg COMMIT_SHA="e8cc07e4208073c62d0bb642fef7529956f4452d" \
  --tag bitcoindevproject/bitcoin:disabled-opcodes \
  resources/images/bitcoin/insecure
```

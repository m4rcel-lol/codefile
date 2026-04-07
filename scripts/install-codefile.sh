#!/usr/bin/env bash
set -euo pipefail

REPO="${CODEFILE_REPO:-m4rcel-lol/codefile}"
TAG="${CODEFILE_TAG:-latest}"
INSTALL_DIR="${CODEFILE_INSTALL_DIR:-/usr/local/bin}"
BASHRC_FILE="${HOME}/.bashrc"

need_cmd() {
    if ! command -v "$1" >/dev/null 2>&1; then
        echo "Error: required command '$1' was not found." >&2
        exit 1
    fi
}

resolve_latest_tag() {
    local latest_url
    latest_url="$(curl -fsSLI -o /dev/null -w '%{url_effective}' "https://github.com/${REPO}/releases/latest")"
    basename "${latest_url}"
}

download_binary() {
    local effective_tag="$1"
    local url="https://github.com/${REPO}/releases/download/${effective_tag}/codefile"
    local out="$2"

    echo "Downloading ${url} ..."
    curl -fsSL "${url}" -o "${out}"
    chmod +x "${out}"
}

install_binary() {
    local src="$1"
    local target="${INSTALL_DIR}/codefile"

    if [ ! -d "${INSTALL_DIR}" ]; then
        mkdir -p "${INSTALL_DIR}" 2>/dev/null || true
    fi

    if [ -w "${INSTALL_DIR}" ]; then
        install -m 0755 "${src}" "${target}"
        return 0
    fi

    if command -v sudo >/dev/null 2>&1; then
        sudo install -m 0755 "${src}" "${target}"
        return 0
    fi

    INSTALL_DIR="${HOME}/.local/bin"
    mkdir -p "${INSTALL_DIR}"
    target="${INSTALL_DIR}/codefile"
    install -m 0755 "${src}" "${target}"
}

ensure_bash_path() {
    if [ "${INSTALL_DIR}" = "/usr/local/bin" ]; then
        return 0
    fi

    local export_line="export PATH=\"${INSTALL_DIR}:\$PATH\""
    if [ ! -f "${BASHRC_FILE}" ] || ! grep -Fq "${export_line}" "${BASHRC_FILE}"; then
        echo "${export_line}" >> "${BASHRC_FILE}"
        echo "Added ${INSTALL_DIR} to PATH in ${BASHRC_FILE}"
    fi
}

main() {
    need_cmd curl
    need_cmd install

    local effective_tag="${TAG}"
    if [ "${TAG}" = "latest" ]; then
        effective_tag="$(resolve_latest_tag)"
    fi

    local tmp
    tmp="$(mktemp)"
    trap 'rm -f "${tmp}"' EXIT

    download_binary "${effective_tag}" "${tmp}"
    install_binary "${tmp}"
    ensure_bash_path

    echo "Codefile installed to ${INSTALL_DIR}/codefile"
    echo "Restart your shell or run: source ${BASHRC_FILE}"
    "${INSTALL_DIR}/codefile" version
}

main "$@"

#!/usr/bin/env bash
set -euo pipefail

REPO="${CODEFILE_REPO:-m4rcel-lol/codefile}"
TAG="${CODEFILE_TAG:-latest}"
INSTALL_DIR="${CODEFILE_INSTALL_DIR:-/usr/local/bin}"
FALLBACK_INSTALL_DIR="${CODEFILE_FALLBACK_DIR:-${HOME}/.local/bin}"
BASHRC_FILE="${HOME}/.bashrc"
PATH_UPDATED=0

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
    local chosen_dir="${INSTALL_DIR}"
    local target

    if [ ! -d "${chosen_dir}" ]; then
        mkdir -p "${chosen_dir}" 2>/dev/null || true
    fi

    target="${chosen_dir}/codefile"
    if [ -w "${chosen_dir}" ]; then
        install -m 0755 "${src}" "${target}"
        echo "${chosen_dir}"
        return 0
    fi

    if command -v sudo >/dev/null 2>&1; then
        sudo install -m 0755 "${src}" "${target}"
        echo "${chosen_dir}"
        return 0
    fi

    chosen_dir="${FALLBACK_INSTALL_DIR}"
    mkdir -p "${chosen_dir}"
    target="${chosen_dir}/codefile"
    install -m 0755 "${src}" "${target}"
    echo "${chosen_dir}"
}

ensure_bash_path() {
    local target_dir="$1"
    local export_line="export PATH=\"\$PATH:${target_dir}\""

    if [[ ":${PATH}:" == *":${target_dir}:"* ]]; then
        return 0
    fi

    if [ -f "${BASHRC_FILE}" ] && grep -Fq "${export_line}" "${BASHRC_FILE}"; then
        return 0
    fi

    if [ ! -f "${BASHRC_FILE}" ]; then
        touch "${BASHRC_FILE}"
    fi

    echo "${export_line}" >> "${BASHRC_FILE}"
    echo "Added ${target_dir} to PATH in ${BASHRC_FILE}"
    PATH_UPDATED=1
    return 0
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

    local final_install_dir
    download_binary "${effective_tag}" "${tmp}"
    final_install_dir="$(install_binary "${tmp}")"
    ensure_bash_path "${final_install_dir}"

    echo "Codefile installed to ${final_install_dir}/codefile"
    if [ "${PATH_UPDATED}" -eq 1 ]; then
        echo "Bash PATH updated. Restart Bash or run: source ${BASHRC_FILE}"
    fi
    "${final_install_dir}/codefile" version
}

main "$@"

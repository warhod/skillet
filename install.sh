#!/usr/bin/env zsh

set -euo pipefail

ROOT="${0:A:h}"
cd "$ROOT"

UV_INSTALLER_VERSION="0.11.7"
UV_INSTALLER_URL="https://github.com/astral-sh/uv/releases/download/${UV_INSTALLER_VERSION}/uv-installer.sh"
UV_INSTALLER_SHA256="efed99618cb5c31e4e36a700ab7c3698e83c0ae0f3c336714043d0f932c8d32c"

info() {
  printf "%s\n" "$*"
}

ensure_uv_on_path() {
  if command -v uv >/dev/null 2>&1; then
    info "Found uv: $(uv --version)"
    info "Skipping installer because uv is already on PATH."
    return
  fi

  info "uv was not found on PATH."
  info "This repo can bootstrap uv using Astral's official installer."
  info "  URL: ${UV_INSTALLER_URL}"
  info "  Expected SHA256: ${UV_INSTALLER_SHA256}"
  info "This downloads and executes the installer script in your user context (no sudo)."
  printf "Proceed with uv bootstrap? [y/N]: "
  read -r consent
  if [[ ! "${consent:l}" =~ ^(y|yes)$ ]]; then
    info "Cancelled by user."
    exit 1
  fi

  tmp_installer="$(mktemp)"
  trap 'rm -f "${tmp_installer}"' EXIT

  info "Downloading pinned uv installer (${UV_INSTALLER_VERSION})..."
  curl -LsSf "${UV_INSTALLER_URL}" -o "${tmp_installer}"

  actual_sha="$(shasum -a 256 "${tmp_installer}" | awk '{print $1}')"
  if [[ "${actual_sha}" != "${UV_INSTALLER_SHA256}" ]]; then
    info "Checksum verification failed."
    info "Expected: ${UV_INSTALLER_SHA256}"
    info "Actual:   ${actual_sha}"
    exit 1
  fi

  info "Checksum verified. Installing uv..."
  sh "${tmp_installer}"

  export PATH="${HOME}/.local/bin:${PATH}"
  if ! command -v uv >/dev/null 2>&1; then
    info "uv installation completed but uv is still not on PATH."
    info "Try adding ~/.local/bin to your shell profile and rerun."
    exit 1
  fi

  info "Installed uv: $(uv --version)"
}

main() {
  ensure_uv_on_path

  if [[ ! -f "${ROOT}/pyproject.toml" ]]; then
    info "Run this script from the skillet source repository (expected src/skillet and pyproject.toml)."
    exit 1
  fi

  info "Syncing a project-local .venv under ${ROOT}/.venv (nothing is installed globally)."
  uv sync --all-groups

  info "Running «skillet install» in: $(pwd)"
  info "This copies bundled skills into .skillet/skills/, applies .skillet/sources.json, and regenerates IDE helper files for this directory."
  uv run skillet install "$@"
}

main "$@"

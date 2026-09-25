#!/usr/bin/env sh

synology_dsm_secret_deploy() {
  _cdomain="$1"
  _syno_host="${_cdomain%%.*}"
  _syno_pwfile="/run/secrets/dsm_password_${_syno_host}"

  if [ ! -s "$_syno_pwfile" ]; then
    _err "No DSM password for $_syno_host: $_syno_pwfile is missing or empty"
    return 1
  fi

  SYNO_USERNAME="${SYNO_USERNAME:-acme}"
  SYNO_PASSWORD="$(cat "$_syno_pwfile")"
  HTTPS_INSECURE=1
  export SYNO_USERNAME SYNO_PASSWORD HTTPS_INSECURE

  . "$_SCRIPT_HOME/deploy/synology_dsm.sh"
  synology_dsm_deploy "$@"
  _syno_rc=$?

  _cleardeployconf SYNO_PASSWORD
  _cleardeployconf SYNO_USERNAME
  return $_syno_rc
}

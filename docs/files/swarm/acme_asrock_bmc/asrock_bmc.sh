#!/usr/bin/env sh

asrock_bmc_deploy() {
  _cdomain="$1"
  _ckey="$2"
  _cfullchain="$5"

  if [ -z "$ASROCK_BMC_URL" ] || [ -z "$ASROCK_BMC_USER" ]; then
    _err "ASROCK_BMC_URL and ASROCK_BMC_USER must be set"
    return 1
  fi
  _asrock_pwfile="${ASROCK_BMC_PASSWORD_FILE:-/run/secrets/asrock_bmc_password}"
  if [ ! -s "$_asrock_pwfile" ]; then
    _err "BMC password file $_asrock_pwfile is missing or empty"
    return 1
  fi

  _asrock_tmp="$(mktemp -d)"
  printf '%s' "$(cat "$_asrock_pwfile")" >"$_asrock_tmp/pw"

  _asrock_curl() {
    curl --silent --show-error --insecure --max-time 60 \
      --cookie "$_asrock_tmp/jar" --cookie-jar "$_asrock_tmp/jar" \
      --output "$_asrock_tmp/out" --write-out '%{http_code}' "$@"
  }

  _code="$(_asrock_curl --data-urlencode "username=$ASROCK_BMC_USER" \
    --data-urlencode "password@$_asrock_tmp/pw" "$ASROCK_BMC_URL/api/session")"
  rm -f "$_asrock_tmp/pw"
  if [ "$_code" != "200" ]; then
    _err "BMC login failed: HTTP $_code"
    rm -rf "$_asrock_tmp"
    return 1
  fi
  _csrf="$(jq -r .CSRFToken "$_asrock_tmp/out")"

  _code="$(_asrock_curl --header "X-CSRFTOKEN: $_csrf" \
    --form "new_certificate=@$_cfullchain" --form "new_private_key=@$_ckey" \
    "$ASROCK_BMC_URL/api/settings/ssl/certificate")"
  if [ "$_code" != "200" ] || [ "$(jq -r .cc "$_asrock_tmp/out" 2>/dev/null)" != "0" ]; then
    _err "BMC rejected the certificate: HTTP $_code $(head -c 200 "$_asrock_tmp/out")"
    _asrock_curl --header "X-CSRFTOKEN: $_csrf" --request DELETE "$ASROCK_BMC_URL/api/session" >/dev/null
    rm -rf "$_asrock_tmp"
    return 1
  fi

  _code="$(_asrock_curl --header "X-CSRFTOKEN: $_csrf" "$ASROCK_BMC_URL/api/settings/ssl/certificate-info")"
  if [ "$_code" = "200" ]; then
    cp "$_asrock_tmp/out" "$_asrock_tmp/info"
    _code="$(_asrock_curl --header "X-CSRFTOKEN: $_csrf" --header 'Content-Type: application/json' \
      --request PUT --data "@$_asrock_tmp/info" "$ASROCK_BMC_URL/api/settings/ssl/certificate-info")"
  fi
  if [ "$_code" != "200" ]; then
    _err "certificate uploaded, but saving certificate-info failed: HTTP $_code"
  fi

  _asrock_curl --header "X-CSRFTOKEN: $_csrf" --request DELETE "$ASROCK_BMC_URL/api/session" >/dev/null
  rm -rf "$_asrock_tmp"
  [ "$_code" = "200" ] || return 1
  _info "Certificate for $_cdomain installed on $ASROCK_BMC_URL"
  return 0
}

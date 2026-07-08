#!/usr/bin/env bats
# systemd_units.bats — asserções estáticas dos units + scratch do applier.
# Guarda de regressão dos bugs pegos no red-team (a operação real roda sob systemd,
# que os testes de comportamento não exercitam; estes asserts travam a regressão).
# ADR-018 Fase 1 · issue #1513

D="${BATS_TEST_DIRNAME}/.."

@test "deployer.service preserva o RuntimeDirectory (handoff sobrevive ao oneshot)" {
  grep -q '^RuntimeDirectoryPreserve=yes' "$D/systemd/aprender-deployer.service"
}

@test "applier.service NAO monta o pai /run/aprender-deployer como RW (so o handoff)" {
  # a linha de ReadWritePaths do applier nao pode conceder o pai inteiro
  run grep '^ReadWritePaths=' "$D/systemd/aprender-applier.service"
  [ "$status" -eq 0 ]
  # deve conter o subdir handoff, e NAO o pai isolado
  [[ "$output" == *"/run/aprender-deployer/handoff"* ]]
  [[ "$output" != *"aprender-applier /run/aprender-deployer "* ]]
}

@test "applier.service e deployer.service: sem docker.sock" {
  grep -q 'InaccessiblePaths=.*docker.sock' "$D/systemd/aprender-applier.service"
  grep -q 'InaccessiblePaths=.*docker.sock' "$D/systemd/aprender-deployer.service"
}

@test "apply.sh nao grava lock/payload em RUN_DIR (usa APPLIER_STATE_DIR)" {
  ! grep -q '\${RUN_DIR}/applier.lock' "$D/apply.sh"
  ! grep -q '\${RUN_DIR}/payload' "$D/apply.sh"
  grep -q '\${APPLIER_STATE_DIR}/applier.lock' "$D/apply.sh"
  grep -q '\${APPLIER_STATE_DIR}/payload' "$D/apply.sh"
}

@test "ambos os services: hardening minimo presente" {
  for u in aprender-deployer aprender-applier; do
    grep -q '^NoNewPrivileges=yes'   "$D/systemd/$u.service"
    grep -q '^ProtectSystem=strict'  "$D/systemd/$u.service"
    grep -q '^CapabilityBoundingSet=$' "$D/systemd/$u.service"
  done
}

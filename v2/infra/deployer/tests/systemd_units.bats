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

# CUIDADO com `! comando` dentro de um @test: sob errexit o `!` ISENTA o comando de
# abortar (POSIX), e o bats julga o teste pelo status FINAL do corpo. Uma negacao
# seguida de qualquer assert positivo vira decoracao — passa sempre. Estas duas
# assercoes ficaram sem dentes desde a Fase 1 (descoberto em 2026-07-10, testando o
# proprio teste). Use `run` + `[ "$status" -ne 0 ]`, que reprova de verdade.
@test "apply.sh nao grava lock/payload em RUN_DIR (usa APPLIER_STATE_DIR)" {
  run grep -q '\${RUN_DIR}/applier.lock' "$D/apply.sh"
  [ "$status" -ne 0 ]
  run grep -q '\${RUN_DIR}/payload' "$D/apply.sh"
  [ "$status" -ne 0 ]
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

# O systemd IGNORA RuntimeMaxSec em Type=oneshot e avisa no journal:
#   "RuntimeMaxSec= has no effect in combination with Type=oneshot. Ignoring."
# Quem limita o tempo de vida e o TimeoutStartSec. Manter RuntimeMaxSec seria
# config que mente sobre o que protege (pego no journal ao reinstalar a 0.2.0).
@test "units oneshot: TimeoutStartSec presente, RuntimeMaxSec ausente" {
  for u in aprender-deployer aprender-applier; do
    grep -q '^Type=oneshot'     "$D/systemd/$u.service"
    grep -q '^TimeoutStartSec=' "$D/systemd/$u.service"
    run grep -q '^RuntimeMaxSec=' "$D/systemd/$u.service"
    [ "$status" -ne 0 ]
  done
}

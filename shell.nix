let
  pkgs = import (fetchTarball
    "https://github.com/NixOS/nixpkgs/archive/50ab793786d9.tar.gz") { };
  unstable = import (fetchTarball
    "https://github.com/NixOS/nixpkgs/archive/400de68cd101.tar.gz") { };

in pkgs.mkShell {
  # Runtime deps copied into the production Docker image.
  dependencies = [ pkgs.python312 pkgs.nodejs_22 ];

  # Everything needed to build inside Docker (no dev tools).
  buildDeps = [ pkgs.python312 pkgs.nodejs_22 unstable.uv pkgs.cacert ];

  buildInputs = [
    pkgs.python312
    unstable.nodejs_22
    unstable.uv
    pkgs.postgresql_17
    pkgs.ripgrep
    unstable.gh
    pkgs.git
    pkgs.cacert
    pkgs.shellcheck
    pkgs.shfmt
    pkgs.nixfmt
    pkgs.jq
    pkgs.curl
  ];

  shellHook = ''
    export PROJECT_NAME="$(basename $(dirname $(pwd)))-$(basename $(pwd))"
    export PROJECT_PATH="$(pwd)"

    source upstream/setup_environment.sh
    source helpers.sh

    echo "$PROJECT_NAME ready."
  '';
}

setup() {
    npm install
    uv sync
}

export PS1='\[\033[00m\]\u\[\033[0;33m\]@\[\033[00m\]\h\[\033[0;33m\] $(super_cwd_global)\[\033[00m\]: '

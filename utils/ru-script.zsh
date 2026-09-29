 #!/usr/bin/env zsh
 # скрипт для терминала zsh нужно вставить в конфиг zshrc в вашей системе

ru() {
    if [[ $# -eq 0 ]]; then
        if [[ -t 0 ]]; then
            echo "Использование:"
            echo "  ru <команда> [аргументы]   — выполнить команду и перевести вывод"
            echo "  ru -t <текст>              — перевести текст"
            echo "  <команда> | ru             — перевести stdin"
            return 1
        fi
        python3 ~/.zsh/translate.py
        return
    fi

    if [[ "$1" == "-t" || "$1" == "--text" ]]; then
        shift
        if [[ $# -eq 0 ]]; then
            python3 ~/.zsh/translate.py
            return
        fi
        echo "$*" | python3 ~/.zsh/translate.py
        return
    fi

    "$@" 2>&1 | python3 ~/.zsh/translate.py
    return ${pipestatus[1]}
}
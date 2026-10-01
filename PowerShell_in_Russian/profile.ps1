# Функция ru — перевод вывода терминала на русский
# Требует: Python 3.10+, библиотека requests, скрипт $HOME\.zsh\translate.py

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

function ru {
    $hasPipeInput = $MyInvocation.ExpectingInput

    # Справка
    if ($args.Count -eq 0 -and -not $hasPipeInput) {
        Write-Host "Использование:"
        Write-Host "  ru КОМАНДА [аргументы]   - выполнить команду и перевести вывод"
        Write-Host "  ru -t ТЕКСТ              - перевести текст"
        Write-Host "  КОМАНДА | ru             - перевести stdin"
        return
    }

    # Режим текста
    if ($args.Count -gt 0 -and ($args[0] -eq "-t" -or $args[0] -eq "--text")) {
        $textToTranslate = $args[1..($args.Count-1)] -join " "
        $textToTranslate | python "$HOME\.zsh\translate.py"
        return
    }

    # Режим команды
    if (-not $hasPipeInput) {
        $cmd = $args[0]
        if ($args.Count -gt 1) {
            $cmdArgs = $args[1..($args.Count-1)]
            & $cmd @cmdArgs 2>&1 | python "$HOME\.zsh\translate.py"
        } else {
            & $cmd 2>&1 | python "$HOME\.zsh\translate.py"
        }
        return
    }

    # Режим пайпа
    $input | python "$HOME\.zsh\translate.py"
}
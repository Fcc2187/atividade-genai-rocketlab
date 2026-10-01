$ErrorActionPreference = 'Stop'
$runtimePath = Join-Path $PSScriptRoot 'runtime\llamafile.exe'
$weightsPath = Join-Path $PSScriptRoot 'models\Qwen3.5-9B-Q5_K_S.gguf'
if (-not (Test-Path -LiteralPath $runtimePath -PathType Leaf)) { throw 'Runtime ausente; veja docs/INSTALACAO_MODELO.md.' }
if (-not (Test-Path -LiteralPath $weightsPath -PathType Leaf)) { throw 'Pesos ausentes; veja docs/INSTALACAO_MODELO.md.' }
& $runtimePath -m $weightsPath --server --host 127.0.0.1 --port 8081 --alias qwen3.5-9b --ctx-size 8192 --parallel 1 --jinja --gpu disable -ngl 0 --no-agent --no-ui --cors-origins localhost --threads 4
if ($LASTEXITCODE -ne 0) { throw "llamafile encerrou com codigo $LASTEXITCODE" }

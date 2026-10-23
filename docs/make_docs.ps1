# 两遍生成文档：先出占位目录量页码，再回填真实页码
#
# 用法： pwsh -File docs\make_docs.ps1
# 依赖： Python 3.8+（python-docx / python-pptx）、带 PyMuPDF 的解释器、LibreOffice
$ErrorActionPreference = "Continue"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

if ($env:PYTHON) { $py = $env:PYTHON } else { $py = "python" }
if ($env:PYTHON_PDF) { $pyPdf = $env:PYTHON_PDF } else { $pyPdf = $py }
if ($env:NODE) { $node = $env:NODE } else { $node = "node" }
$cli = $env:LO_CLI                     # LibreOffice Kit 的 cli.js

$toc = Join-Path $root "docs\_toc"
$pages = Join-Path $root "docs\_pages"
$pdf1 = Join-Path $root "docs\_pdf1"
foreach ($d in @($toc, $pages, $pdf1, (Join-Path $root "docs\pdf"))) {
    New-Item -ItemType Directory -Force -Path $d | Out-Null
}

function Convert-Doc($docx, $target) {
    if (-not $cli) { Write-Output "    跳过转换（未设置 LO_CLI）"; return }
    Remove-Item $target -Force -ErrorAction SilentlyContinue
    & $node $cli convert --input $docx --output $target 2>&1 | Out-Null
}

Write-Output "=== 第 1 轮：占位目录 ==="
& $py docs\build_docs.py --toc-dir $toc 2>&1 | Select-Object -Last 3
& $py docs\build_report.py --toc-dir $toc 2>&1 | Select-Object -Last 2

Write-Output "=== 第 1 轮转 PDF（量页码用）==="
$docs = @("1-需求说明书", "2-设计文档", "3-测试报告", "5-项目汇报")
foreach ($d in $docs) {
    $out = Join-Path $pdf1 "$d.pdf"
    Convert-Doc (Join-Path $root "docs\$d.docx") $out
    Write-Output ("  {0} -> {1}" -f $d, $(if (Test-Path $out) { "OK" } else { "失败" }))
}

Write-Output "=== 量页码 ==="
& $pyPdf docs\build_toc_map.py --toc $toc --pdf $pdf1 --out $pages 2>&1

Write-Output "=== 第 2 轮：回填真实页码 ==="
& $py docs\build_docs.py --toc-dir $toc --pages $pages 2>&1 | Select-Object -Last 3
& $py docs\build_report.py --toc-dir $toc --pages $pages 2>&1 | Select-Object -Last 2

Write-Output "=== 第 2 轮转最终 PDF ==="
foreach ($d in $docs) {
    $out = Join-Path $root "docs\pdf\$d.pdf"
    Convert-Doc (Join-Path $root "docs\$d.docx") $out
    if (Test-Path $out) {
        Write-Output ("  {0}: {1:N0} KB" -f $d, ((Get-Item $out).Length / 1KB))
    }
}

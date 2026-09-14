$word = New-Object -ComObject Word.Application
$word.Visible = $false
try {
    $docxFile = Get-ChildItem -Path . -Filter "*InsurMinds*Atualizado*.docx" | Select-Object -First 1
    if ($docxFile) {
        $docxPath = $docxFile.FullName
        $pdfPath = [System.IO.Path]::ChangeExtension($docxPath, ".pdf")
        Write-Host "Converting $docxPath to $pdfPath..."
        $doc = $word.Documents.Open($docxPath)
        $doc.SaveAs([ref]$pdfPath, [ref]17)
        $doc.Close()
        Write-Host "PDF generated successfully at $pdfPath"
    } else {
        Write-Host "DOCX file not found."
    }
} catch {
    Write-Host "Error during conversion: $_"
} finally {
    $word.Quit()
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($word) | Out-Null
    [System.GC]::Collect()
    [System.GC]::WaitForPendingFinalizers()
}

# convert_to_pdf.ps1
$word = New-Object -ComObject Word.Application
$word.Visible = $false

$docPath = "C:\Users\rohit\work\GUI files\Pi_HMI\PI_HMI_v1_lc\docs\handover\InsituMicron_DAQ_Rig_Technical_Handover_Manual_V1.0.docx"
$pdfPath = [System.IO.Path]::ChangeExtension($docPath, ".pdf")

Write-Output "Processing: $docPath"
$doc = $word.Documents.Open($docPath)

# Update all fields including TOC
$doc.Fields.Update()

# Configure compact TOC styling so entire TOC fits cleanly
try {
    $s1 = $doc.Styles.Item("TOC 1")
    $s1.Font.Size = 9.5
    $s1.ParagraphFormat.SpaceBefore = 2
    $s1.ParagraphFormat.SpaceAfter = 1
    $s1.ParagraphFormat.LineSpacingRule = 0
} catch {}

try {
    $s2 = $doc.Styles.Item("TOC 2")
    $s2.Font.Size = 8.5
    $s2.ParagraphFormat.SpaceBefore = 0.5
    $s2.ParagraphFormat.SpaceAfter = 0.5
    $s2.ParagraphFormat.LineSpacingRule = 0
} catch {}

foreach ($toc in $doc.TablesOfContents) {
    $toc.Update()
}
$doc.Fields.Update()

# Save the updated docx with refreshed fields
$doc.Save()

# Export to PDF (17 = wdFormatPDF)
$wdFormatPDF = 17
$doc.SaveAs([ref]$pdfPath, [ref]$wdFormatPDF)

$pages = $doc.ComputeStatistics(2) # 2 = wdStatisticPages
Write-Output "SUCCESS: $pdfPath ($pages pages)"

$doc.Close([ref]$false)
$word.Quit()
Write-Output "PDF Conversion complete."

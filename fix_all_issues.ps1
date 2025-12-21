# PowerShell script to fix all 7 issues

$adminHtmlPath = "frontend\admin.html"
$content = Get-Content $adminHtmlPath -Raw

# FIX 1 & 2: Update plan values to match backend
$content = $content -replace '<option value="Basic - 1 Month">Basic - 1 Month</option>', '<option value="1 Month">1 Month</option>'
$content = $content -replace '<option value="Premium - 6 Months">Premium - 6 Months</option>', '<option value="3 Months">3 Months</option>'
$content = $content -replace '<option value="Elite - 12 Months">Elite - 12 Months</option>', '<option value="6 Months">6 Months</option>'
$content = $content -replace '<option value="Ultimate - 24 Months">Ultimate - 24 Months</option>', '<option value="12 Months">12 Months</option>'

# FIX 3: Add IST timezone conversion function
$istFunction = @'
    // Convert UTC to IST (Indian Standard Time)
    function toIST(dateString) {
        if (!dateString) return 'Never';
        const date = new Date(dateString);
        return date.toLocaleString('en-IN', {
            timeZone: 'Asia/Kolkata',
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
            hour12: true
        });
    }

    // ============================================================================
'@

$content = $content -replace '    // ============================================================================', $istFunction

# FIX 4: Update timestamp displays to use IST
$content = $content -replace '\$\{new Date\(c\.timestamp\)\.toLocaleString\(\)\}', '${toIST(c.timestamp)}'
$content = $content -replace 'new Date\(user\.last_login\)\.toLocaleString\(\)', 'toIST(user.last_login)'
$content = $content -replace 'const timestamp = new Date\(entry\.timestamp\)\.toLocaleString\(''en-IN'', \{[^}]+\}\);', 'const timestamp = toIST(entry.timestamp);'

# FIX 5: Add icon column to partners table header
$content = $content -replace '<th>Partner Name</th>\s+<th>Gym Count</th>', '<th>Partner Name</th>
                            <th>Icon</th>
                            <th>Gym Count</th>'

# FIX 6: Add icon display in partners table rows
$oldPartnerRow = 'table.innerHTML = partners.map\(partner => `\s+<tr>\s+<td>\$\{partner\.name\}</td>\s+<td>\$\{partner\.gym_count \|\| 0\}</td>'
$newPartnerRow = @'
table.innerHTML = partners.map(partner => {
                const icon = partner.icon ?
                    (partner.icon.startsWith('data:') ?
                        `<img src="${partner.icon}" style="max-width: 30px; max-height: 30px; border-radius: 4px;">` :
                        `<span style="font-size: 24px;">${partner.icon}</span>`) :
                    'N/A';
                return `
                <tr>
                    <td>${partner.name}</td>
                    <td>${icon}</td>
                    <td>${partner.gym_count || 0}</td>
'@
$content = $content -replace [regex]::Escape($oldPartnerRow), $newPartnerRow

# Save the file
$content | Set-Content $adminHtmlPath -NoNewline

Write-Host "Fixed admin.html successfully!"

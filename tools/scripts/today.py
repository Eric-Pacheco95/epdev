"""Print today's date as YYYY-MM-DD. Replaces powershell Get-Date in bat wrappers."""
from datetime import date
print(date.today())

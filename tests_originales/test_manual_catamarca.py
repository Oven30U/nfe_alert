from CloudflareBypasser import CloudflareBypasser
from DrissionPage import ChromiumPage

driver = ChromiumPage()
driver.get("https://dgrentas.arca.gob.ar/rentascuA/principal.aspx")

cf_bypasser = CloudflareBypasser(driver)
cf_bypasser.bypass()

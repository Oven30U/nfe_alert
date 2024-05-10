# Using CSS selectors
await page.fill('input[name="username"]', 'my_username')  # Fill an input with name "username"
await page.click('.submit-button')  # Click on an element with class "submit-button"

# Using XPath
await page.fill('xpath=//input[@name="username"]', 'my_username')  # Fill an input with name "username"
await page.click('xpath=//button[contains(text(), "Submit")]')  # Click on a button with text "Submit"

# Using text content
await page.click('text="Continue"')  # Click on an element with text "Continue"

# Using id
await page.fill('#username', 'my_username')  # Fill an input with id "username"
await page.click('#submit')  # Click on an element with id "submit"

# Using attributes
await page.fill('[placeholder="Username"]', 'my_username')  # Fill an input with placeholder "Username"
await page.click('[title="Submit"]')  # Click on an element with title "Submit"

# Navega a la URL especificada
await page.goto('https://www.example.com')

# Hace clic en un elemento que coincide con el selector especificado
await page.click('button#submit')

# Llena un campo de entrada que coincide con el selector especificado con el valor proporcionado
await page.fill('input[name="username"]', 'my_username')

# Escribe el texto en un campo de entrada que coincide con el selector especificado
await page.type('input[name="username"]', 'my_username')

# Simula la pulsación de una tecla en un elemento que coincide con el selector especificado
await page.press('input[name="username"]', 'Enter')

# Marca una casilla de verificación o un botón de opción que coincide con el selector especificado
await page.check('input[name="terms"]')

# Desmarca una casilla de verificación o un botón de opción que coincide con el selector especificado
await page.uncheck('input[name="terms"]')

# Selecciona una opción en un elemento <select> que coincide con el selector especificado
await page.select_option('select#country', 'US')

# Espera hasta que un elemento que coincide con el selector especificado aparezca en la página
await page.wait_for_selector('div.content')

# Espera hasta que la navegación de la página se complete
await page.wait_for_navigation()

# Ejecuta un script de JavaScript en el contexto de la página
result = await page.evaluate('() => document.title')

# Toma una captura de pantalla de la página
await page.screenshot(path='screenshot.png')
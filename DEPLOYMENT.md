# Deployment Guide: Smart Pharmacy App for Mobile and Web

To use your Smart Pharmacy application on a mobile device and deploy it as a professional app, follow these steps.

## 1. Local Network Access (Fastest for Testing)
You can access the app from your phone right now if it's on the same Wi-Fi as your computer.

1.  **Find your Computer's IP**:
    -   Open Terminal/Command Prompt.
    -   Type `ipconfig` (Windows) or `ifconfig` (Mac/Linux).
    -   Look for `IPv4 Address` (e.g., `192.168.1.10`).
2.  **Run the App**:
    -   Make sure your Flask app is running.
    -   By default, it runs on `http://127.0.0.1:5000`.
3.  **Access on Mobile**:
    -   On your phone's browser, type: `http://192.168.1.10:5000` (Replace with your IP).

---

## 2. Cloud Deployment (For Public Access)
To use the app from anywhere, you should deploy it to a cloud provider.

### Option A: Render (Free/Easy)
1.  **Create a `requirements.txt`**:
    -   Run: `pip freeze > requirements.txt`
2.  **Create a `Procfile`**:
    -   Create a file named `Procfile` (no extension) with this content:
        `web: gunicorn app:app`
3.  **Push to GitHub**:
    -   Create a repository and upload your code.
4.  **Connect to Render**:
    -   Go to [Render.com](https://render.com/), create a "Web Service", and connect your GitHub repo.

---

## 3. Convert to a Mobile App (PWA)
The easiest way to make this feel like a mobile app without writing Java/Swift is to make it a **Progressive Web App (PWA)**. This adds an "Add to Home Screen" button on phones.

### Step 1: Add a Manifest File
Create `static/manifest.json`:
```json
{
  "name": "Smart Pharmacy",
  "short_name": "Pharmacy",
  "start_url": "/",
  "display": "standalone",
  "background_color": "#ffffff",
  "theme_color": "#007bff",
  "icons": [
    {
      "src": "/static/icon.png",
      "sizes": "192x192",
      "type": "image/png"
    }
  ]
}
```

### Step 2: Add Service Worker
Create `static/sw.js` (empty file is enough for basic PWA detection).

### Step 3: Link in HTML
Add this to the `<head>` of your `index.html`:
```html
<link rel="manifest" href="/static/manifest.json">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
```

---

## 4. Hardware Requirements for Mobile
-   **Camera Permissions**: The app uses the camera for scanning. When prompted on your phone, click **Allow**.
-   **HTTPS**: Browsers (Chrome/Safari) only allow camera access on `localhost` or over **HTTPS**. If you deploy to the cloud (like Render), it will automatically provide HTTPS.

---

## 5. Recommended Production Stack
-   **Backend**: Flask (Current)
-   **Server**: Gunicorn (for Linux) or Waitress (for Windows)
-   **Database**: SQLite (Current) - *Note: On platforms like Heroku, SQLite files reset. Use Render or a persistent volume for the `.db` file.*

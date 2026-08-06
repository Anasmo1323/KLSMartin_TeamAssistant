# TechnoWave - MMC Medical Instrument Portal

A modern, interactive Next.js web application designed for doctors and representatives at Madinaty Medical Centre (MMC) to browse, select, and request KLS Martin surgical instrument sets.

## Features

* **Secure Access**: Discipline-based access codes (e.g., `8899` for Admin) unlock specific catalog areas.
* **Interactive Catalog**: Browse instrument families, view high-res images (Cloudinary integration), and add individual pieces or complete sets to the cart.
* **Amazon-style Checkout**: A dedicated, full-screen review interface to double-check quantities, customer details, and add custom notes before submission.
* **Smart Autofill**: The portal remembers the doctor's Name, Hospital, and contact details across sessions (stored locally).
* **Automated Email Notifications**: Real-time HTML email notifications are sent to the hospital supply department upon order submission, powered by the **Resend API**.
* **Admin Dashboard**: 
  * View all past submissions with timestamps and statuses.
  * Configure who receives order notification emails directly from the UI.
  * Export submission data to Excel for external tracking.
* **Theme Customization**: Built-in ☀️/🌙 toggle in the navigation bar to switch between the default Light Mode and a custom "Premium Dark Glassmorphism" theme.

## Tech Stack

* **Frontend**: Next.js (App Router), React, CSS Modules (Glassmorphism design)
* **Backend**: Next.js API Routes (`/api/notify`)
* **Database**: Firebase Firestore (for storing submissions and email configurations)
* **Emails**: Resend SDK
* **Hosting**: Designed for Vercel / Node.js environments.

## Getting Started

1. Clone the repository.
2. Ensure you have the `.env.local` file configured with your Firebase credentials and Resend API Key:
   ```env
   RESEND_API_KEY=re_xxxxxxxxxxxxxxxxx
   RESEND_FROM_EMAIL=onboarding@resend.dev
   ```
3. Install dependencies:
   ```bash
   npm install
   ```
4. Run the development server:
   ```bash
   npm run dev
   ```
5. Open [http://localhost:3000](http://localhost:3000) to view the portal.

## Admin Access
To access the admin dashboard, enter the code `8899` on the homepage or navigate to `/admin`.

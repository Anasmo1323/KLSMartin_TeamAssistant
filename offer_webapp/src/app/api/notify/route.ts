import { NextResponse } from 'next/server';
import nodemailer from 'nodemailer';
import { db } from '../../../lib/firebase';
import { doc, getDoc } from 'firebase/firestore';
import * as XLSX from 'xlsx';

export async function POST(req: Request) {
  try {
    const { submissionId, items, customer, totalItems, wantsExcelReceipt } = await req.json();

    // 1. Fetch notification emails from Firebase
    const configDoc = await getDoc(doc(db, 'config', 'notifications'));
    let adminEmails: string[] = [];
    if (configDoc.exists()) {
      adminEmails = configDoc.data().emails || [];
    }

    // Safety check for Gmail credentials
    if (!process.env.GMAIL_USER || !process.env.GMAIL_APP_PASSWORD) {
      console.error("GMAIL_USER or GMAIL_APP_PASSWORD is missing from environment variables.");
      return NextResponse.json({ success: false, error: "Server misconfigured. Missing Gmail credentials." }, { status: 500 });
    }

    // 2. Build HTML Email Draft
    const itemsHtml = items.map((item: any) =>
      `<li><strong>${item.categoryName} &gt; ${item.setName || 'General'}</strong>: ${item.qty}x ${item.groupName} (${item.code})</li>`
    ).join('');

    const adminHtmlContent = `
      <div style="font-family: sans-serif; max-width: 600px; margin: auto;">
        <h2 style="color: #00c8ff;">New Submission Received</h2>
        <p>A new instrument request has been successfully submitted through the Portal.</p>
        
        <h3>Customer Details</h3>
        <table style="width: 100%; border-collapse: collapse; margin-bottom: 1.5rem;">
          <tr>
            <td style="padding: 8px; border: 1px solid #ddd;"><strong>Name:</strong></td>
            <td style="padding: 8px; border: 1px solid #ddd;">${customer.title} ${customer.name}</td>
          </tr>
          <tr>
            <td style="padding: 8px; border: 1px solid #ddd;"><strong>Hospital:</strong></td>
            <td style="padding: 8px; border: 1px solid #ddd;">${customer.hospital}</td>
          </tr>
          <tr>
            <td style="padding: 8px; border: 1px solid #ddd;"><strong>Phone:</strong></td>
            <td style="padding: 8px; border: 1px solid #ddd;">${customer.phone || 'N/A'}</td>
          </tr>
          <tr>
            <td style="padding: 8px; border: 1px solid #ddd;"><strong>Email:</strong></td>
            <td style="padding: 8px; border: 1px solid #ddd;">${customer.email || 'N/A'}</td>
          </tr>
          <tr>
            <td style="padding: 8px; border: 1px solid #ddd;"><strong>Notes:</strong></td>
            <td style="padding: 8px; border: 1px solid #ddd;">${customer.notes || 'N/A'}</td>
          </tr>
        </table>

        <h3>Order Summary (Total Items: ${totalItems})</h3>
        <ul>
          ${itemsHtml}
        </ul>

        <p style="margin-top: 2rem; color: #777; font-size: 0.9rem;">
          Submission ID: <strong>${submissionId}</strong><br/>
          <em>You can view the full details in the Admin Dashboard.</em>
        </p>
      </div>
    `;

    const hasOrthoItem = items.some((item: any) =>
      (item.categoryName || '').toUpperCase().includes('ORTHO') ||
      (item.setName || '').toUpperCase().includes('ORTHO') ||
      (item.groupName || '').toUpperCase().includes('ORTHO') ||
      (item.code || '').toUpperCase().includes('ORTHO')
    );

    const doctorHtmlContent = `
      <div style="font-family: sans-serif; max-width: 600px; margin: auto;">
        <h2 style="color: #00c8ff;">Greetings from Technowave Team - KLSMartin</h2>
        <p>Dear ${customer.title} ${customer.name},</p>
        <p>Thank you for submitting your instrument request Technowave - KLSMartin Portal.</p>
        <p>Attached to this email is an Excel sheet containing your complete requested order list.</p>
        
        <h3>Order Summary (Total Items: ${totalItems})</h3>
        <ul>
          ${itemsHtml}
        </ul>

        <div style="margin-top: 2rem;">
          <p><strong>Helpful Links:</strong></p>
          <ul>
            <li style="margin-bottom: 0.5rem;"><a href="https://www.klsmartin.com/en/media-library/brochures-catalogs-flyers/#%7B%22fulltext%22:%22%22,%22applicationField%22:%22%22,%22topic%22:%2220%22,%22language%22:%22%22,%22media%22:%22%22,%22page%22:%220%22%7D">KLS Martin Brochures</a></li>
            <li style="margin-bottom: 0.5rem;"><a href="https://www.klsmartin.com/shop/en/">KLS Martin Shop</a></li>
            ${hasOrthoItem ? '<li style="margin-bottom: 0.5rem;"><a href="https://www.klsmartin.com/mediathek/91-350-73-02_Nexos_Pelvis_Access_and_repositioning.pdf">Nexos Pelvis Access and repositioning</a></li>' : ''}
          </ul>
        </div>

        <p style="margin-top: 2rem; color: #777; font-size: 0.9rem;">
          Submission ID: <strong>${submissionId}</strong>
        </p>

        <div style="margin-top: 3rem; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;">
          <p style="margin-bottom: 1.5rem; color: #1e477a; font-weight: bold; font-size: 13px;">Don’t hesitate to contact me if you require any further information.</p>
          
          <img src="https://klsmcc.vercel.app/Technowave.png" alt="Technowave" width="220" style="margin-bottom: 1.5rem; display: block; border: none; outline: none;" />
          
          <p style="margin: 0; color: #1e477a; font-family: 'Times New Roman', Times, serif; font-size: 18px; font-weight: bold;">Eng. Albear Emil Ayoub</p>
          <p style="margin: 4px 0 2px 0; color: #1e477a; font-size: 13px; font-weight: bold;">Sales Manager</p>
          
          <p style="margin: 2px 0; color: #1e477a; font-size: 13px;">Tel :+202-27498312/ 3 / 4  EXT:212</p>
          <p style="margin: 2px 0; color: #1e477a; font-size: 13px;">Fax:+202-27498309</p>
          <p style="margin: 2px 0; color: #1e477a; font-size: 13px;">Mob:  +201222247653</p>
          
          <p style="margin: 6px 0 2px 0; color: #1e477a; font-size: 13px;">Sky Tower, Ring Road,</p>
          <p style="margin: 2px 0; color: #1e477a; font-size: 13px;">Besides Bavarian Auto (BMW)</p>
          <p style="margin: 2px 0; color: #1e477a; font-size: 13px;">Katamia, Cairo - Egypt</p>
          
          <br/>
          <p style="margin: 1rem 0 0 0; font-size: 11px; color: #000; font-weight: bold; line-height: 1.4; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;">
            This e-mail may contain confidential and/or privileged information. If you are not the intended recipient (or have received this e-mail in error) please notify the sender immediately and destroy this e-mail.<br/>
            Any unauthorized copying, disclosure, or distribution of the material in this e-mail is strictly forbidden.
          </p>
        </div>
      </div>
    `;

    let attachments = [];
    // Always generate Excel attachment for admin & doctor
    const excelData = items.map((item: any) => ({
      'Category': item.categoryName,
      'Set': item.setName || 'General',
      'Item Group': item.groupName,
      'Code': item.code,
      'Description': item.optionDesc || '',
      'Quantity': item.qty
    }));

    const ws = XLSX.utils.json_to_sheet(excelData);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, "Requested Items");

    const buffer = XLSX.write(wb, { type: 'buffer', bookType: 'xlsx' });

    attachments.push({
      filename: `MMC_Request_${submissionId}.xlsx`,
      content: buffer
    });

    // 3. Send Email using Nodemailer
    const transporter = nodemailer.createTransport({
      service: 'gmail',
      auth: {
        user: process.env.GMAIL_USER,
        pass: process.env.GMAIL_APP_PASSWORD,
      },
    });

    let messageId = null;

    if (adminEmails.length > 0) {
      const adminInfo = await transporter.sendMail({
        from: `"Portal Notifications" <${process.env.GMAIL_USER}>`,
        to: adminEmails.join(', '),
        subject: `New Request Submission - ${customer.hospital}`,
        html: adminHtmlContent,
        attachments: attachments,
      });
      messageId = adminInfo.messageId;
      console.log(`Admin notification sent for ${submissionId}. MessageId:`, adminInfo.messageId);
    } else {
      console.log('No admin emails configured. Admin email skipped.');
    }

    if (wantsExcelReceipt && customer.email) {
      const doctorInfo = await transporter.sendMail({
        from: `"Technowave Team - KLSMartin" <${process.env.GMAIL_USER}>`,
        to: customer.email,
        subject: `Your Instrument Request List - Technowave Team - KLSMartin`,
        html: doctorHtmlContent,
        attachments: attachments,
      });
      console.log(`Doctor receipt sent for ${submissionId}. MessageId:`, doctorInfo.messageId);
    }

    return NextResponse.json({ success: true, messageId });

  } catch (error: any) {
    console.error('Error sending notification email:', error);
    return NextResponse.json({ success: false, error: error.message }, { status: 500 });
  }
}

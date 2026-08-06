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
    let emails: string[] = [];
    if (configDoc.exists()) {
      emails = configDoc.data().emails || [];
    }

    if (wantsExcelReceipt && customer.email) {
      if (!emails.includes(customer.email)) {
        emails.push(customer.email);
      }
    }

    if (emails.length === 0) {
      console.log('No notification emails configured.');
      return NextResponse.json({ success: true, message: 'No emails configured' });
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

    const htmlContent = `
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

    let attachments = [];
    if (wantsExcelReceipt) {
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
    }

    // 3. Send Email using Nodemailer
    const transporter = nodemailer.createTransport({
      service: 'gmail',
      auth: {
        user: process.env.GMAIL_USER,
        pass: process.env.GMAIL_APP_PASSWORD,
      },
    });

    const info = await transporter.sendMail({
      from: `"Portal Notifications" <${process.env.GMAIL_USER}>`,
      to: emails.join(', '),
      subject: `New Request Submission - ${customer.hospital}`,
      html: htmlContent,
      attachments: attachments.length > 0 ? attachments : undefined,
    });

    console.log(`Notification email sent via Gmail for submission ${submissionId}. MessageId:`, info.messageId);
    return NextResponse.json({ success: true, messageId: info.messageId });

  } catch (error: any) {
    console.error('Error sending notification email:', error);
    return NextResponse.json({ success: false, error: error.message }, { status: 500 });
  }
}

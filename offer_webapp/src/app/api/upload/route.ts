import { NextResponse } from 'next/server';
import { storage } from '../../../lib/firebase';
import { ref, uploadString, getDownloadURL } from 'firebase/storage';

export async function POST(request: Request) {
  try {
    const { customerId, catalogData } = await request.json();

    if (!customerId || !catalogData) {
      return NextResponse.json({ error: 'Missing parameters' }, { status: 400 });
    }

    const filename = `catalogs/${customerId}_catalog.json`;
    const storageRef = ref(storage, filename);
    const jsonString = JSON.stringify(catalogData);

    // Upload using Firebase SDK (Node environment bypasses CORS)
    await uploadString(storageRef, jsonString, 'raw', { contentType: 'application/json' });
    const downloadURL = await getDownloadURL(storageRef);

    return NextResponse.json({ url: downloadURL });

  } catch (error: any) {
    console.error('Upload Error:', error);
    return NextResponse.json({ error: error.message || 'Internal Server Error' }, { status: 500 });
  }
}

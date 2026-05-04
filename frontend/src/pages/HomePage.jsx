import { useState } from 'react';
import Hero from '../components/Hero';
import UploadCard from '../components/UploadCard';
import ExtractionResults from '../components/ExtractionResults';
import Footer from '../components/Footer';

export default function HomePage() {
  const [extractionResult, setExtractionResult] = useState(null);

  return (
    <div style={{ minHeight: 'calc(100vh - 6rem)', position: 'relative' }}>
      <main>
        <Hero />
        <UploadCard onExtractionComplete={setExtractionResult} />
        {extractionResult && <ExtractionResults data={extractionResult} />}
      </main>
      <Footer />
    </div>
  );
}

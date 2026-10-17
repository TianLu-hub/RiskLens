import { RiskDashboard } from '@/components/RiskDashboard';
import { LanguageProvider } from '@/components/LanguageProvider';

export default function Home() {
  return (
    <LanguageProvider>
      <RiskDashboard />
    </LanguageProvider>
  );
}

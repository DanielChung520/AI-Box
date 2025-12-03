import { toast } from "sonner";
import { cn } from "@/lib/utils";
import { useLanguage } from "@/contexts/languageContext";

// Empty component
export function Empty() {
  const { t } = useLanguage();

  return (
    <div className={cn("flex h-full items-center justify-center cursor-pointer")} onClick={() => toast(t('common.comingSoon'))}>
      {t('common.empty')}
    </div>
  );
}

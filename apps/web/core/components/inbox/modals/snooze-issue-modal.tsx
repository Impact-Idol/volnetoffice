import { useState, useEffect } from "react";
// ui
import { useTranslation } from "@plane/i18n";
import { Button } from "@plane/propel/button";
import { Calendar } from "@plane/propel/calendar";
import { EModalPosition, EModalWidth, ModalCore } from "@plane/ui";

export type InboxIssueSnoozeModalProps = {
  isOpen: boolean;
  value: Date | undefined;
  onConfirm: (value: Date) => void;
  handleClose: () => void;
};

export function InboxIssueSnoozeModal(props: InboxIssueSnoozeModalProps) {
  const { isOpen, handleClose, value, onConfirm } = props;
  // states - initialize with value or null to avoid hydration mismatch
  const [date, setDate] = useState<Date | null>(value || null);

  // Set current date on client only
  useEffect(() => {
    if (!date) {
      setDate(new Date());
    }
  }, []);
  //hooks
  const { t } = useTranslation();

  return (
    <ModalCore isOpen={isOpen} handleClose={handleClose} position={EModalPosition.CENTER} width={EModalWidth.XXL}>
      <div className="flex h-full w-full flex-col gap-y-1 px-5 py-8 sm:p-6">
        <Calendar
          className="rounded-md border border-subtle p-3"
          captionLayout="dropdown"
          selected={date ? new Date(date) : undefined}
          defaultMonth={date ? new Date(date) : undefined}
          onSelect={(date: Date | undefined) => {
            if (!date) return;
            setDate(date);
          }}
          mode="single"
          disabled={[
            {
              before: new Date(),
            },
          ]}
        />
        <Button
          variant="primary"
          disabled={!date}
          onClick={() => {
            if (!date) return;
            handleClose();
            onConfirm(date);
          }}
        >
          {t("inbox_issue.actions.snooze")}
        </Button>
      </div>
    </ModalCore>
  );
}

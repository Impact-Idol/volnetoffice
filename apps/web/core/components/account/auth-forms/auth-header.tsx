import { observer } from "mobx-react";
import useSWR from "swr";
import { useTranslation } from "@plane/i18n";
import type { IWorkspaceMemberInvitation } from "@plane/types";
// components
import { LogoSpinner } from "@/components/common/logo-spinner";
import { WorkspaceLogo } from "@/components/workspace/logo";
// helpers
import { EAuthModes, EAuthSteps } from "@/helpers/authentication.helper";
// services
import { WorkspaceService } from "@/plane-web/services";

type TAuthHeader = {
  workspaceSlug: string | undefined;
  invitationId: string | undefined;
  invitationEmail: string | undefined;
  authMode: EAuthModes;
  currentAuthStep: EAuthSteps;
};

const Titles = {
  [EAuthModes.SIGN_IN]: {
    [EAuthSteps.EMAIL]: {
      header: "Make an Impact. Change Lives.",
      subHeader: "Welcome back to Impact Idol.",
    },
    [EAuthSteps.PASSWORD]: {
      header: "Make an Impact. Change Lives.",
      subHeader: "Welcome back to Impact Idol.",
    },
    [EAuthSteps.UNIQUE_CODE]: {
      header: "Make an Impact. Change Lives.",
      subHeader: "Welcome back to Impact Idol.",
    },
  },
  [EAuthModes.SIGN_UP]: {
    [EAuthSteps.EMAIL]: {
      header: "Make an Impact. Change Lives.",
      subHeader: "Create your Impact Idol account.",
    },
    [EAuthSteps.PASSWORD]: {
      header: "Make an Impact. Change Lives.",
      subHeader: "Create your Impact Idol account.",
    },
    [EAuthSteps.UNIQUE_CODE]: {
      header: "Make an Impact. Change Lives.",
      subHeader: "Create your Impact Idol account.",
    },
  },
};

const workSpaceService = new WorkspaceService();

export const AuthHeader = observer(function AuthHeader(props: TAuthHeader) {
  const { workspaceSlug, invitationId, invitationEmail, authMode, currentAuthStep } = props;
  // plane imports
  const { t } = useTranslation();

  const { data: invitation, isLoading } = useSWR(
    workspaceSlug && invitationId ? `WORKSPACE_INVITATION_${workspaceSlug}_${invitationId}` : null,
    async () => workspaceSlug && invitationId && workSpaceService.getWorkspaceInvitation(workspaceSlug, invitationId),
    {
      revalidateOnFocus: false,
      shouldRetryOnError: false,
    }
  );

  const getHeaderSubHeader = (
    step: EAuthSteps,
    mode: EAuthModes,
    invitation: IWorkspaceMemberInvitation | undefined,
    email: string | undefined
  ) => {
    if (invitation && email && invitation.email === email && invitation.workspace) {
      const workspace = invitation.workspace;
      return {
        header: (
          <div className="relative inline-flex items-center gap-2">
            {t("common.join")}{" "}
            <WorkspaceLogo logo={workspace?.logo_url} name={workspace?.name} classNames="size-9 flex-shrink-0" />{" "}
            {workspace.name}
          </div>
        ),
        subHeader:
          mode == EAuthModes.SIGN_UP
            ? "Create an account to join this volunteer organization."
            : "Log in to join this volunteer organization.",
      };
    }

    return Titles[mode][step];
  };

  const { header, subHeader } = getHeaderSubHeader(currentAuthStep, authMode, invitation || undefined, invitationEmail);

  if (isLoading)
    return (
      <div className="flex h-full w-full items-center justify-center">
        <LogoSpinner />
      </div>
    );

  return <AuthHeaderBase subHeader={subHeader} header={header} />;
});

type TAuthHeaderBase = {
  header: React.ReactNode;
  subHeader: string;
};

export function AuthHeaderBase(props: TAuthHeaderBase) {
  return (
    <div className="flex flex-col gap-1">
      <span className="text-h4-semibold text-primary">{props.header}</span>
      <span className="text-h4-semibold text-placeholder">{props.subHeader}</span>
    </div>
  );
}

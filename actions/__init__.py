"""
Custom actions for the enhanced email assistant.
"""
# Import basic actions
from actions.basic_email_actions import ActionDeleteEmail, ActionMarkAsRead

# Import improved email actions
from actions.improved_email_actions import ActionListEmails, ActionReadSelectedEmail, ValidateSelectedEmail, ActionNavigateEmails

# Import email reply actions
from actions.improved_email_reply_actions import ActionInitiateReply, ActionGenerateReplyDraft, ActionSendReply, ActionEditReplyDraft

# Import email organization actions
from actions.improved_email_organize_actions import ActionGetLabelSuggestions, ActionApplySelectedLabel

# Import special handling actions
from actions.special_email_handling import ActionCheckForNoReply

# Import validation actions
from actions.validate_email_response import ValidateEmailResponse, ActionSelectInputPrompt


# For Rasa to discover the actions
all_actions = [
    # Email actions
    ActionListEmails(),
    ActionReadSelectedEmail(), 
    ActionNavigateEmails(),  # This is the fixed version
    ValidateSelectedEmail(),
    
    # Email operations
    ActionDeleteEmail(),
    ActionMarkAsRead(),
    
    # Reply actions
    ActionInitiateReply(),
    ActionGenerateReplyDraft(),
    ActionEditReplyDraft(),  # New edit action
    ActionSendReply(),
    
    # Organization actions
    ActionGetLabelSuggestions(),
    ActionApplySelectedLabel(),
    
    # Special handling actions
    ActionCheckForNoReply(),

    # Validation actions
    ValidateEmailResponse(),
    ActionSelectInputPrompt(),
]
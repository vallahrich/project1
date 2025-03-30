"""
Custom actions for the enhanced email assistant.
"""
# Import required actions
from actions.basic_email_actions import ActionDeleteEmail, ActionMarkAsRead
from actions.improved_email_actions import ActionListEmails, ActionReadSelectedEmail, ActionNavigateEmails, ValidateSelectedEmail
from actions.improved_email_organize_actions import ActionGetLabelSuggestions, ActionApplySelectedLabel
from actions.improved_email_reply_actions import ActionInitiateReply, ActionGenerateReplyDraft, ActionSendReply

# For Rasa to discover the actions
all_actions = [
    # Email actions
    ActionListEmails(),
    ActionReadSelectedEmail(),
    ActionNavigateEmails(),
    ValidateSelectedEmail(),
    
    # Email operations
    ActionDeleteEmail(),
    ActionMarkAsRead(),
    
    # Reply actions
    ActionInitiateReply(),
    ActionGenerateReplyDraft(),
    ActionSendReply(),
    
    # Organization actions
    ActionGetLabelSuggestions(),
    ActionApplySelectedLabel(),
]
import resend

from app.core.config import settings

# Configure Resend with API key
resend.api_key = settings.RESEND_API_KEY


def send_email(
    to_email: str, subject: str, html_content: str, text_content: str = None
):
    """
    Send an email via Resend API.

    Args:
        to_email: Recipient email address
        subject: Email subject
        html_content: HTML content of the email
        text_content: Plain text content (optional, fallback)
    """
    try:
        # Prepare email parameters
        params = {
            "from": f"{settings.EMAIL_FROM_NAME} <{settings.EMAIL_FROM_ADDRESS}>",
            "to": [to_email],
            "subject": subject,
            "html": html_content,
        }

        # Add text content if provided
        if text_content:
            params["text"] = text_content

        # Send email using Resend
        email = resend.Emails.send(params)
        print(f"✅ Email sent successfully to {to_email} (ID: {email['id']})")
        return email
    except Exception as e:
        print(f"❌ Failed to send email to {to_email}: {str(e)}")
        raise


def send_invitation_email(
    to_email: str, invite_link: str, team_name: str, inviter_name: str = None
):
    """
    Send a team invitation email.

    Args:
        to_email: Recipient email address
        invite_link: Full invitation acceptance link
        team_name: Name of the team
        inviter_name: Name of the person who sent the invitation
    """
    subject = f"You've been invited to join {team_name} on BridgeAI"

    # HTML content
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="margin: 0; padding: 0; font-family: Arial, sans-serif; background-color: #f4f4f4;">
        <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f4f4f4; padding: 20px;">
            <tr>
                <td align="center">
                    <table width="600" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                        <!-- Header -->
                        <tr>
                            <td style="background-color: #341bab; padding: 30px; text-align: center;">
                                <h1 style="color: #ffffff; margin: 0; font-size: 28px;">BridgeAI</h1>
                            </td>
                        </tr>
                        
                        <!-- Content -->
                        <tr>
                            <td style="padding: 40px 30px;">
                                <h2 style="color: #333333; margin: 0 0 20px 0; font-size: 24px;">You've been invited!</h2>
                                
                                <p style="color: #666666; font-size: 16px; line-height: 1.6; margin: 0 0 20px 0;">
                                    {"<strong>" + inviter_name + "</strong> has" if inviter_name else "You've been"} invited you to join <strong>{team_name}</strong> on BridgeAI.
                                </p>
                                
                                <p style="color: #666666; font-size: 16px; line-height: 1.6; margin: 0 0 30px 0;">
                                    Click the button below to accept the invitation and join the team.
                                </p>
                                
                                <!-- Button -->
                                <table width="100%" cellpadding="0" cellspacing="0">
                                    <tr>
                                        <td align="center" style="padding: 20px 0;">
                                            <a href="{invite_link}" 
                                               style="display: inline-block; padding: 15px 40px; background-color: #341bab; color: #ffffff; text-decoration: none; border-radius: 5px; font-size: 16px; font-weight: bold;">
                                                Accept Invitation
                                            </a>
                                        </td>
                                    </tr>
                                </table>
                                
                                <p style="color: #999999; font-size: 14px; line-height: 1.6; margin: 30px 0 0 0;">
                                    Or copy and paste this link into your browser:
                                </p>
                                <p style="color: #341bab; font-size: 14px; word-break: break-all; margin: 10px 0 0 0;">
                                    {invite_link}
                                </p>
                                
                                <p style="color: #999999; font-size: 14px; line-height: 1.6; margin: 30px 0 0 0;">
                                    <strong>Note:</strong> This invitation will expire in 7 days.
                                </p>
                            </td>
                        </tr>
                        
                        <!-- Footer -->
                        <tr>
                            <td style="background-color: #f8f8f8; padding: 20px 30px; text-align: center; border-top: 1px solid #eeeeee;">
                                <p style="color: #999999; font-size: 12px; margin: 0;">
                                    © 2025 BridgeAI. All rights reserved.
                                </p>
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """

    # Plain text content (fallback)
    text_content = f"""
    You've been invited to join {team_name} on BridgeAI!
    
    {"" if not inviter_name else f"{inviter_name} has invited you to join their team."}
    
    Click the link below to accept the invitation:
    {invite_link}
    
    This invitation will expire in 7 days.
    
    © 2025 BridgeAI. All rights reserved.
    """

    send_email(to_email, subject, html_content, text_content)


def send_password_reset_email(to_email: str, otp_code: str):
    """
    Send a password reset email with an OTP code.

    Args:
        to_email: Recipient email address
        otp_code: 6-digit verification code
    """
    subject = "Reset your BridgeAI Password"

    # HTML content
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="margin: 0; padding: 0; font-family: Arial, sans-serif; background-color: #f4f4f4;">
        <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f4f4f4; padding: 20px;">
            <tr>
                <td align="center">
                    <table width="600" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                        <tr style="background-color: #341bab;">
                            <td style="padding: 30px; text-align: center;">
                                <h1 style="color: #ffffff; margin: 0; font-size: 28px;">BridgeAI</h1>
                            </td>
                        </tr>
                        <tr>
                            <td style="padding: 40px 30px;">
                                <h2 style="color: #333333; margin: 0 0 20px 0; font-size: 24px;">Password Reset</h2>
                                <p style="color: #666666; font-size: 16px; line-height: 1.6; margin: 0 0 20px 0;">
                                    We received a request to reset your password. Use the following code to continue:
                                </p>
                                <div style="background-color: #f8f8f8; padding: 20px; text-align: center; border-radius: 8px; margin: 30px 0;">
                                    <span style="font-size: 32px; font-weight: bold; color: #341bab; letter-spacing: 5px;">{otp_code}</span>
                                </div>
                                <p style="color: #666666; font-size: 14px; line-height: 1.6; margin: 0;">
                                    This code will expire in 15 minutes. If you did not request this, please ignore this email.
                                </p>
                            </td>
                        </tr>
                        <tr style="background-color: #f8f8f8;">
                            <td style="padding: 20px; text-align: center; border-top: 1px solid #eeeeee;">
                                <p style="color: #999999; font-size: 12px; margin: 0;">© 2025 BridgeAI. All rights reserved.</p>
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """

    # Plain text content
    text_content = f"""
    Reset your BridgeAI Password
    
    Use the following code to reset your password: {otp_code}
    
    This code will expire in 15 minutes. If you did not request this, please ignore this email.
    
    © 2025 BridgeAI. All rights reserved.
    """

    send_email(to_email, subject, html_content, text_content)

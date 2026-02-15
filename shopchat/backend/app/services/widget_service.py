"""
Widget script generation service for embeddable chat widgets.

Generates JavaScript snippets that can be embedded on external websites
to display the ShopChat chatbot widget. The script handles widget
initialization, theming, positioning, and communication with the
ShopChat API.

For Developers:
    ``generate_widget_snippet()`` produces a self-contained JavaScript
    snippet that creates an iframe-based chat widget. The snippet is
    configurable for position, theme, greeting, and brand colors.
    ``generate_widget_script()`` returns the full JavaScript file
    content served at ``/api/v1/widget/{widget_id}/script.js``.

For QA Engineers:
    Test that generated snippets contain the correct widget_id and
    configuration values. Verify that different position/theme
    combinations produce valid JavaScript. Test the script.js
    endpoint returns correct Content-Type headers.

For Project Managers:
    The widget script is the entry point for embedding ShopChat on
    external websites. Users copy a one-line script tag from the
    dashboard and paste it into their store's HTML.

For End Users:
    Copy the embed code from your chatbot settings and paste it
    into your website's HTML to add the AI chat widget.
"""

from app.config import settings


def generate_widget_snippet(
    widget_id: str,
    config: dict | None = None,
) -> str:
    """
    Generate an embeddable HTML/JavaScript snippet for the chat widget.

    Creates a ``<script>`` tag that loads the widget script from the
    ShopChat API and initializes it with the given configuration.

    Args:
        widget_id: The chatbot's unique widget key.
        config: Optional configuration dict with keys:
            - position: 'bottom-right' or 'bottom-left' (default: 'bottom-right')
            - theme: 'light' or 'dark' (default: 'light')
            - greeting: Custom greeting text (default: 'Hi! How can I help?')
            - primary_color: Hex color for the widget (default: '#6366f1')
            - text_color: Hex color for widget text (default: '#ffffff')

    Returns:
        HTML string containing the embeddable ``<script>`` tag.
    """
    if config is None:
        config = {}

    position = config.get("position", "bottom-right")
    theme = config.get("theme", "light")
    greeting = config.get("greeting", "Hi! How can I help?")
    primary_color = config.get("primary_color", "#6366f1")
    text_color = config.get("text_color", "#ffffff")

    base_url = settings.cors_origins.split(",")[0].strip()

    return (
        f'<script src="{base_url}/api/v1/widget/{widget_id}/script.js" '
        f'data-widget-id="{widget_id}" '
        f'data-position="{position}" '
        f'data-theme="{theme}" '
        f'data-greeting="{greeting}" '
        f'data-primary-color="{primary_color}" '
        f'data-text-color="{text_color}" '
        f"async></script>"
    )


def generate_widget_script(
    widget_id: str,
    config: dict | None = None,
) -> str:
    """
    Generate the full JavaScript content for the widget script endpoint.

    This is the content served at ``GET /api/v1/widget/{widget_id}/script.js``.
    It creates the chat widget UI, handles user interactions, and communicates
    with the ShopChat chat API.

    Args:
        widget_id: The chatbot's unique widget key.
        config: Optional widget configuration dict with keys:
            - position: Widget position ('bottom-right' or 'bottom-left').
            - theme: Color theme ('light' or 'dark').
            - greeting: Initial greeting message.
            - primary_color: Brand primary color (hex).
            - text_color: Brand text color (hex).
            - chatbot_name: Display name of the chatbot.

    Returns:
        JavaScript source code as a string.
    """
    if config is None:
        config = {}

    position = config.get("position", "bottom-right")
    theme = config.get("theme", "light")
    greeting = config.get("greeting", "Hi! How can I help?")
    primary_color = config.get("primary_color", "#6366f1")
    text_color = config.get("text_color", "#ffffff")
    chatbot_name = config.get("chatbot_name", "ShopChat")

    # Background and text colors based on theme
    bg_color = "#ffffff" if theme == "light" else "#1f2937"
    fg_color = "#111827" if theme == "light" else "#f9fafb"
    border_color = "#e5e7eb" if theme == "light" else "#374151"

    # Position CSS
    pos_css = "right: 20px;" if position == "bottom-right" else "left: 20px;"

    api_base = f"{settings.llm_gateway_url.rstrip('/')}"
    # Use the ShopChat backend URL for API calls from the widget
    api_url = f"http://localhost:{settings.service_port}"

    return f"""(function() {{
  'use strict';

  var WIDGET_ID = '{widget_id}';
  var API_URL = '{api_url}/api/v1/widget';
  var VISITOR_ID = 'visitor_' + Math.random().toString(36).substr(2, 9);

  // Create widget container
  var container = document.createElement('div');
  container.id = 'shopchat-widget';
  container.innerHTML = `
    <div id="sc-toggle" style="
      position: fixed; bottom: 20px; {pos_css}
      width: 60px; height: 60px; border-radius: 50%;
      background: {primary_color}; color: {text_color};
      display: flex; align-items: center; justify-content: center;
      cursor: pointer; box-shadow: 0 4px 12px rgba(0,0,0,0.15);
      font-size: 24px; z-index: 99999;
      transition: transform 0.2s ease;
    " onmouseover="this.style.transform='scale(1.1)'"
       onmouseout="this.style.transform='scale(1)'">
      &#128172;
    </div>
    <div id="sc-chat" style="
      display: none; position: fixed; bottom: 90px; {pos_css}
      width: 380px; height: 520px; border-radius: 16px;
      background: {bg_color}; border: 1px solid {border_color};
      box-shadow: 0 8px 32px rgba(0,0,0,0.12);
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      z-index: 99999; overflow: hidden;
      display: flex; flex-direction: column;
    ">
      <div style="
        padding: 16px; background: {primary_color}; color: {text_color};
        font-weight: 600; font-size: 16px; border-radius: 16px 16px 0 0;
      ">{chatbot_name}</div>
      <div id="sc-messages" style="
        flex: 1; overflow-y: auto; padding: 16px;
        display: flex; flex-direction: column; gap: 8px;
      ">
        <div style="
          background: {primary_color}20; color: {fg_color};
          padding: 10px 14px; border-radius: 12px;
          max-width: 80%; font-size: 14px;
        ">{greeting}</div>
      </div>
      <div style="
        padding: 12px; border-top: 1px solid {border_color};
        display: flex; gap: 8px;
      ">
        <input id="sc-input" type="text" placeholder="Type a message..."
          style="
            flex: 1; padding: 10px 14px; border: 1px solid {border_color};
            border-radius: 24px; font-size: 14px; outline: none;
            background: {bg_color}; color: {fg_color};
          "
        />
        <button id="sc-send" style="
          width: 40px; height: 40px; border-radius: 50%;
          background: {primary_color}; color: {text_color};
          border: none; cursor: pointer; font-size: 16px;
        ">&#9654;</button>
      </div>
    </div>
  `;

  document.body.appendChild(container);

  var chatEl = document.getElementById('sc-chat');
  var isOpen = false;

  document.getElementById('sc-toggle').addEventListener('click', function() {{
    isOpen = !isOpen;
    chatEl.style.display = isOpen ? 'flex' : 'none';
  }});

  function addMessage(text, role) {{
    var msgs = document.getElementById('sc-messages');
    var div = document.createElement('div');
    div.style.cssText = role === 'user'
      ? 'background: {primary_color}; color: {text_color}; padding: 10px 14px; border-radius: 12px; max-width: 80%; font-size: 14px; align-self: flex-end;'
      : 'background: {primary_color}20; color: {fg_color}; padding: 10px 14px; border-radius: 12px; max-width: 80%; font-size: 14px;';
    div.textContent = text;
    msgs.appendChild(div);
    msgs.scrollTop = msgs.scrollHeight;
  }}

  async function sendMessage() {{
    var input = document.getElementById('sc-input');
    var text = input.value.trim();
    if (!text) return;

    input.value = '';
    addMessage(text, 'user');

    try {{
      var resp = await fetch(API_URL + '/chat', {{
        method: 'POST',
        headers: {{ 'Content-Type': 'application/json' }},
        body: JSON.stringify({{
          widget_key: WIDGET_ID,
          visitor_id: VISITOR_ID,
          message: text
        }})
      }});
      var data = await resp.json();
      addMessage(data.message, 'assistant');
    }} catch (e) {{
      addMessage('Sorry, something went wrong. Please try again.', 'assistant');
    }}
  }}

  document.getElementById('sc-send').addEventListener('click', sendMessage);
  document.getElementById('sc-input').addEventListener('keypress', function(e) {{
    if (e.key === 'Enter') sendMessage();
  }});
}})();"""

document.addEventListener("DOMContentLoaded", function() {
    // Check if Socket.IO is actually loaded
    if (typeof io === "undefined") {
      console.error("Socket.IO not found. Make sure your script reference is correct and not blocked by SRI.");
      return;
    }
  
    const socket = io();
  
    // Log successful connection
    socket.on("connect", () => {
      console.log("Socket connected!");
    });
  
    // Log connection errors
    socket.on("connect_error", (err) => {
      console.error("Socket connection error:", err);
    });
  
    // Listen for incoming bot messages
    socket.on("receive_message", function(data) {
      const chatBox = document.getElementById("chat-box");
      chatBox.innerHTML += `<div class="message bot"><div class="bubble"><strong>Bot:</strong> ${data.message}</div></div>`;
      chatBox.scrollTop = chatBox.scrollHeight;
    });
  
    // Listen for custom error events from the server (if any)
    socket.on("error", function(data) {
      const chatBox = document.getElementById("chat-box");
      chatBox.innerHTML += `<div class="message bot"><div class="bubble"><strong>Error:</strong> ${data.error}</div></div>`;
    });
  
    // Function to send a message
    function sendMessage() {
      const input = document.getElementById("user-input");
      const message = input.value.trim();
      if (!message) return;
      input.value = '';
      const chatBox = document.getElementById("chat-box");
      chatBox.innerHTML += `<div class="message user"><div class="bubble"><strong>You:</strong> ${message}</div></div>`;
      socket.emit("send_message", { message: message });
    }
  
    // Event listeners for button click and Enter key
    document.getElementById("send-button").addEventListener("click", sendMessage);
    document.getElementById("user-input").addEventListener("keypress", function(event) {
      if (event.key === "Enter") {
        sendMessage();
      }
    });
  });
  
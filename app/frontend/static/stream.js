export async function stream_text(stream_url, contentDiv, chatMessages, speed = 1, max_speed = 60) {
    const streamResponse = await fetch(stream_url, {method: 'POST'}); // POST to bypass ngrok
    const reader = streamResponse.body.getReader();
    const decoder = new TextDecoder();
    
    let buffer = "";       // text waiting to be shown
    let displayed = "";    // text already shown
    let streamDone = false; // track if stream reading is done
    let animationId = null; // track animation frame

    let lastTime = performance.now();

    function typeOut(now) {
        const delta = (now - lastTime) / 1000; // seconds since last frame
        lastTime = now;

        if (buffer.length > 0) {
            // Characters per second = 30 * speed (tweak base rate)
            const charsPerSecond = buffer.length * speed;

            // How many chars to reveal this frame
            const chunkSize = Math.max(1, Math.min(Math.floor(charsPerSecond * delta), max_speed * delta));

            displayed += buffer.slice(0, chunkSize);
            buffer = buffer.slice(chunkSize);

            contentDiv.innerHTML = marked.parse(displayed);
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }

        // Continue animation if buffer has content or stream not done
        if (buffer.length > 0 || !streamDone) {
            animationId = requestAnimationFrame(typeOut);
        }
    }

    // Kick off animation loop
    animationId = requestAnimationFrame(typeOut);

    // Fill buffer from the stream
    while (true) {
        const { value, done } = await reader.read();
        if (done) {
            streamDone = true;
            // Decode any remaining data
            buffer += decoder.decode();
            break;
        }
        buffer += decoder.decode(value, { stream: true });
    }
    
    // Wait for all text to be displayed - poll until buffer is empty
    while (buffer.length > 0) {
        await new Promise(resolve => {
            const checkBuffer = () => {
                if (buffer.length === 0) {
                    resolve();
                } else {
                    requestAnimationFrame(checkBuffer);
                }
            };
            requestAnimationFrame(checkBuffer);
        });
    }
    
    // Final render to ensure all text is shown
    contentDiv.innerHTML = marked.parse(displayed);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

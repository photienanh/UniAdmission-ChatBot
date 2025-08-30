export async function stream_text(stream_url, contentDiv, chatMessages, speed = 1, max_speed = 60) {
    const streamResponse = await fetch(stream_url);
    const reader = streamResponse.body.getReader();
    const decoder = new TextDecoder();
    
    let buffer = "";       // text waiting to be shown
    let displayed = "";    // text already shown

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

        requestAnimationFrame(typeOut);
    }

    // Kick off animation loop
    requestAnimationFrame(typeOut);

    // Fill buffer from the stream
    while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
    }
}

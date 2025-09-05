def build_ffmpeg_cmd(input_url: str, rtmp_destinations: list, use_streamlink=False):
    tee_parts = [f"[f=flv]{dest}" for dest in rtmp_destinations]
    tee_url = "|".join(tee_parts)

    if use_streamlink:
        # input_url is Twitch URL
        input_cmd = ["streamlink", "--stdout", input_url, "best"]
        cmd = input_cmd + [
            "|",
            "ffmpeg", "-y", "-i", "-", 
            "-c:v", "libx264", "-preset", "veryfast", "-tune", "zerolatency",
            "-c:a", "aac", "-b:a", "160k", "-ar", "44100",
            "-f", "tee", tee_url
        ]
        # Note: using shell=True is required if we combine streamlink and ffmpeg as a string
        return " ".join(cmd), True  # return cmd as string + shell flag
    else:
        # normal ffmpeg input
        cmd = [
            "ffmpeg", "-y", "-i", input_url,
            "-c:v", "libx264", "-preset", "veryfast", "-tune", "zerolatency",
            "-c:a", "aac", "-b:a", "160k", "-ar", "44100",
            "-f", "tee", tee_url
        ]
        return cmd, False

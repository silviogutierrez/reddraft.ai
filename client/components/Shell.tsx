import React from "react";

interface Props {
    children: React.ReactNode;
    title?: string;
}

export function Shell(props: Props) {
    return (
        <html lang="en" style={{backgroundColor: "#1a1a2e"}}>
            <head>
                <meta charSet="UTF-8" />
                <meta
                    name="viewport"
                    content="width=device-width, initial-scale=1.0"
                />
                <title>
                    {props.title ?? "Reddit Draft Queue"}
                </title>
                <link
                    rel="preconnect"
                    href="https://fonts.googleapis.com"
                />
                <link
                    rel="preconnect"
                    href="https://fonts.gstatic.com"
                    crossOrigin="anonymous"
                />
                <link
                    href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&display=swap"
                    rel="stylesheet"
                />
            </head>
            <body className="bg-bg text-text font-sans min-h-screen">
                {props.children}
            </body>
        </html>
    );
}

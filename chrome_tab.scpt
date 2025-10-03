-- AppleScript to get current Chrome tab content with optional filtering
-- MODIFIED FOR NON-INTERACTIVE EXECUTION

on run argv
    -- Get the visible text from the current tab
    set visibleText to getChromeTextContent()

    -- Deduplicate the lines of the text
    set dedupedText to my deduplicateLines(visibleText)

    -- Parse arguments to determine filtering behavior
    set doFilter to false
    set useStartKw to ""
    set useEndKw to ""
    set fromStart to false
    set toEnd to false

    if (count of argv) = 0 then
        -- Default: no filtering, return full page
        set doFilter to false
    else if (item 1 of argv is "--no-filter") then
        -- No filtering requested
        set doFilter to false
    else if (item 1 of argv is "--from-start") then
        -- From document start to end keyword
        set fromStart to true
        if (count of argv) > 1 then
            set useEndKw to item 2 of argv
        end if
        set doFilter to true
    else if (count of argv) = 1 then
        -- Only start keyword provided, go to end of document
        set useStartKw to item 1 of argv
        set toEnd to true
        set doFilter to true
    else if (count of argv) = 2 then
        if (item 2 of argv is "--to-end") then
            -- Start keyword to end of document
            set useStartKw to item 1 of argv
            set toEnd to true
            set doFilter to true
        else
            -- Both start and end keywords provided
            set useStartKw to item 1 of argv
            set useEndKw to item 2 of argv
            set doFilter to true
        end if
    end if

    -- Apply filtering based on parsed arguments
    if doFilter is false then
        set the clipboard to dedupedText
        return dedupedText
    else
        -- Determine which filtering function to use
        if fromStart is true then
            set filteredContent to filterFromStart(dedupedText, useEndKw)
        else if toEnd is true then
            set filteredContent to filterToEnd(dedupedText, useStartKw)
        else
            set filteredContent to filterContentBetweenKeywords(dedupedText, useStartKw, useEndKw)
        end if

        if filteredContent is not "" then
            set the clipboard to filteredContent
            return filteredContent
        else
            return dedupedText
        end if
    end if
end run

on deduplicateLines(inputText)
    -- Use awk to perform a robust, case-insensitive, order-preserving deduplication
    set shellCmd to "echo " & quoted form of inputText & " | awk '!seen[tolower($0)]++'"
    try
        set dedupedText to (do shell script shellCmd without altering line endings)
        return dedupedText
    on error errMsg number errNum
        return "Deduplication Error (awk): " & errMsg & " (Code: " & errNum & ")"
    end try
end deduplicateLines

on getChromeContent()
    -- Activate Chrome and get the current tab's content
    tell application "Google Chrome"
        if (count of windows) > 0 then
            set currentTab to active tab of front window
            -- Execute JS to clone the DOM, remove images, links, and SVGs, then return the cleaned HTML
            set pageSource to execute currentTab javascript " \
                (function() { \
                    var cleanDoc = document.documentElement.cloneNode(true); \
                    cleanDoc.querySelectorAll('img, a, svg').forEach(function(el) { el.remove(); }); \
                    return cleanDoc.outerHTML; \
                })();"
            return pageSource
        else
            error "No Chrome window is open"
        end if
    end tell
end getChromeContent

-- Alternative approach to get visible text content
on getChromeTextContent()
    tell application "Google Chrome"
        if (count of windows) > 0 then
            set currentTab to active tab of front window
            -- Get the visible text content instead of HTML
            set pageText to execute currentTab javascript "document.body.innerText"
            return pageText
        else
            error "No Chrome window is open"
        end if
    end tell
end getChromeTextContent

on filterContentBetweenKeywords(content, startKeyword, endKeyword)
    try
        ignoring case
            -- Find the start position of the content after the start keyword
            set startPos to offset of startKeyword in content
            if startPos is 0 then
                return "" -- Start keyword not found
            end if

            -- Adjust position to after the start keyword
            set startPos to startPos + (length of startKeyword)

            -- Find the end position of the content before the end keyword
            set remainingContent to text startPos thru -1 of content
            set endPos to offset of endKeyword in remainingContent
            if endPos is 0 then
                return "" -- End keyword not found
            end if
        end ignoring

        -- Extract the content between the keywords
        set filteredContent to text 1 thru (endPos - 1) of remainingContent

        -- Trim leading and trailing whitespace
        return trimWhitespace(filteredContent)
    on error
        return ""
    end try
end filterContentBetweenKeywords

on filterFromStart(content, endKeyword)
    -- Filter from the start of the document to the end keyword
    try
        ignoring case
            set endPos to offset of endKeyword in content
            if endPos is 0 then
                return "" -- End keyword not found
            end if
        end ignoring

        -- Extract content from start to before the end keyword
        set filteredContent to text 1 thru (endPos - 1) of content
        return trimWhitespace(filteredContent)
    on error
        return ""
    end try
end filterFromStart

on filterToEnd(content, startKeyword)
    -- Filter from the start keyword to the end of the document
    try
        ignoring case
            set startPos to offset of startKeyword in content
            if startPos is 0 then
                return "" -- Start keyword not found
            end if

            -- Adjust position to after the start keyword
            set startPos to startPos + (length of startKeyword)
        end ignoring

        -- Extract content from after start keyword to end
        set filteredContent to text startPos thru -1 of content
        return trimWhitespace(filteredContent)
    on error
        return ""
    end try
end filterToEnd

on trimWhitespace(textStr)
    set whitespace to {" ", "	", return}

    -- Remove leading whitespace
    repeat while (length of textStr > 0) and (character 1 of textStr is in whitespace)
        if length of textStr = 1 then return ""
        set textStr to text 2 thru -1 of textStr
    end repeat

    -- Remove trailing whitespace
    repeat while (length of textStr > 0) and (character -1 of textStr is in whitespace)
        if length of textStr = 1 then return ""
        set textStr to text 1 thru -2 of textStr
    end repeat

    return textStr
end trimWhitespace

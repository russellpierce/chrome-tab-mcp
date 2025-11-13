-- AppleScript to get current Chrome tab content with optional filtering
-- MODIFIED FOR NON-INTERACTIVE EXECUTION

on run argv
    -- Get the visible text from the current tab
    try
        set visibleText to getChromeTextContent()
    on error errMsg number errNum
        return "Error retrieving Chrome content: " & errMsg & " (Code: " & errNum & ")"
    end try

    -- Deduplicate the lines of the text
    try
        set dedupedText to my deduplicateLines(visibleText)
    on error errMsg number errNum
        return "Error deduplicating content: " & errMsg & " (Code: " & errNum & ")"
    end try

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
    -- Use awk to perform robust, case-insensitive, order-preserving deduplication
    -- For large inputs, use a temporary file to avoid command-line length limits
    set textLength to length of inputText

    if textLength > 10000 then
        -- Large input: use temporary file approach
        set tempFile to "/tmp/chrome_tab_input_" & (do shell script "date +%s%N")
        try
            -- Write input to temp file
            do shell script "cat > " & quoted form of tempFile & " <<'EOFDATA'\n" & inputText & "\nEOFDATA"
            -- Process with awk and cleanup
            set dedupedText to (do shell script "awk '!seen[tolower($0)]++' " & quoted form of tempFile & " && rm " & quoted form of tempFile without altering line endings)
            return dedupedText
        on error errMsg number errNum
            do shell script "rm -f " & quoted form of tempFile
            return "Deduplication Error (awk): " & errMsg & " (Code: " & errNum & ")"
        end try
    else
        -- Small input: use direct pipeline approach
        set shellCmd to "printf '%s' " & quoted form of inputText & " | awk '!seen[tolower($0)]++'"
        try
            set dedupedText to (do shell script shellCmd without altering line endings)
            return dedupedText
        on error errMsg number errNum
            return "Deduplication Error (awk): " & errMsg & " (Code: " & errNum & ")"
        end try
    end if
end deduplicateLines

on getChromeTextContent()
    try
        tell application "Google Chrome"
            -- Check if Chrome is running and has windows
            if (count of windows) = 0 then
                error "Chrome has no open windows. Please open Chrome and navigate to a page."
            end if

            try
                set currentTab to active tab of front window
            on error
                error "Unable to access Chrome's active tab. Check Chrome accessibility permissions."
            end try

            -- Get the visible text content via JavaScript
            try
                set pageText to execute currentTab javascript "document.body.innerText"

                -- Check if we got valid content
                if pageText is missing value then
                    error "JavaScript returned null/undefined. The page may not have loaded properly or tab may be a special page (e.g., PDF, blank)."
                end if

                return pageText
            on error jsErr
                error "Failed to extract text from page: " & jsErr
            end try
        end tell
    on error errMsg number errNum
        error "getChromeTextContent Error: " & errMsg & " (Code: " & errNum & ")"
    end try
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
    -- Use sed to efficiently trim leading and trailing whitespace
    set shellCmd to "printf '%s' " & quoted form of textStr & " | sed -e 's/^[[:space:]]*//;s/[[:space:]]*$//'"
    try
        set trimmedText to (do shell script shellCmd without altering line endings)
        return trimmedText
    on error errMsg number errNum
        -- Fallback to original text if sed fails
        return textStr
    end try
end trimWhitespace

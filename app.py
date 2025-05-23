import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import streamlit as st
from openai import OpenAI

# Read API key from Streamlit secrets
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

visited_urls = set()

def get_links(url, base_domain):
    links = {}
    try:
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        anchors = soup.find_all('a', href=True)
        for a in anchors:
            text = a.text.strip()[:100]
            href = urljoin(url, a['href'])
            if urlparse(href).netloc == base_domain and href not in visited_urls:
                links[text] = href
        return links
    except Exception:
        return {}

def crawl_site_recursive(url, base_domain, depth=1):
    if depth == 0 or url in visited_urls:
        return {}
    visited_urls.add(url)
    page_links = get_links(url, base_domain)
    all_links = dict(page_links)
    for link_text, link_href in page_links.items():
        if link_href not in visited_urls:
            deeper_links = crawl_site_recursive(link_href, base_domain, depth - 1)
            all_links.update(deeper_links)
    return all_links

def find_best_link(links_dict, intent_label):
    prompt = f"""
Given the following webpage link texts and their hrefs:

{str(links_dict)}

Which one is the best match for '{intent_label}'?
Return only the href.
"""
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Error: {e}"

# Streamlit UI
st.title("AI Website Crawler")

url_input = st.text_input("Enter a website URL:", "https://www.aerinaacrylicworld.store/")
max_depth = st.slider("Set crawl depth:", 1, 3, 2)

if st.button("Start Crawling"):
    if url_input:
        st.write(f"Crawling: {url_input} with depth={max_depth}")
        parsed = urlparse(url_input)
        domain = parsed.netloc
        visited_urls.clear()

        with st.spinner("Crawling site..."):
            links = crawl_site_recursive(url_input, domain, depth=max_depth)

        st.success(f"Crawled {len(links)} links. Sending to LLM...")

        targets = [
            "Privacy Policy",
            "Terms and Conditions",
            "Refund or Cancellation Policy",
            "Contact Us",
            "Products or Services Page"
        ]

        for label in targets:
            st.write(f"**{label}:**")
            match = find_best_link(links, label)
            st.code(match)
    else:
        st.warning("Please enter a valid URL.")

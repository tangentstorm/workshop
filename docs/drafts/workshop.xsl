<?xml version="1.0" encoding="utf-8"?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">

<xsl:template match="trail">
  <html>
  <head>
    <title><xsl:value-of select="title"/></title>
    <link rel="stylesheet" href="workshop.css"/>
  </head>
  <body>
    <xsl:apply-templates/>
  </body>
  </html>
</xsl:template>

<xsl:template match="title">
   <h1>{:whatever:}</h1>
</xsl:template>


</xsl:stylesheet>

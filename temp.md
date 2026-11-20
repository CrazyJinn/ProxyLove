graph TB
    subgraph EV["Event 行为层（description = 发生了什么）"]
        E1["「陈念来电」<br/>06-12 08:30<br/>以家庭聚餐名义邀约"]
        E2["「陈念安排相亲陈默到地方一看是苏晓禾」<br/>06-14 12:00<br/>到场揭底"]
    end

    I(["Info 事实层（kl=2）<br/>陈念为陈默安排了<br/>与苏晓禾的相亲"])

    C1["Cognition<br/>陈念 · KNOWS<br/>安排者，全程知情"]
    C2["Cognition<br/>陈默 · KNOWS<br/>只知聚餐邀约，到场方知"]

    CN["陈念"]
    CM["陈默"]
    SXH["苏晓禾"]

    E1 -->|"establishes<br/>并列承载（安排起点）"| I
    E2 -->|"establishes<br/>主承载（兑现揭底）"| I
    E2 -->|"forms"| C1
    E2 -->|"forms"| C2
    CN -->|"has_cognition"| C1
    CM -->|"has_cognition"| C2
    C1 -->|"about"| I
    C2 -->|"about"| I

    C3["Cognition<br/>苏晓禾 · ?"]
    SXH -.->|"has_cognition（若知情）"| C3
    C3 -.->|"about（若立）"| I
    E2 -.->|"forms（若知情）"| C3

    classDef event fill:#e8f0fe,stroke:#4285f4
    classDef info fill:#fef7e0,stroke:#f9ab00
    classDef cog fill:#e6f4ea,stroke:#34a853
    classDef char fill:#f3e8fd,stroke:#a142f4
    classDef pending fill:#ffffff,stroke:#999999,stroke-dasharray:4 3
    class E1,E2 event
    class I info
    class C1,C2 cog
    class CN,CM,SXH char
    class C3 pending

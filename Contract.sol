// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

/**
 * @title CivicPulse Municipal Tracker (AI Enhanced)
 * @notice Manages infrastructure reports, AI timelines, and contractor resolution.
 */
contract CivicPulseTracker {

    // ============ 1. State Variables ============
    address public admin; // The AI Agent / Backend System
    uint256 public ticketCounter;

    // ============ 2. Data Structures ============

    enum TicketStatus { 
        OPEN,           // 0: Reported
        IN_PROGRESS,    // 1: AI Assigned / Crew Dispatched
        RESOLVED,       // 2: Fixed & Verified
        REJECTED        // 3: Spam
    }

    enum ReportType {
        IMAGE,          // 0: Camera Upload
        TEXT            // 1: Text Description
    }

    struct Ticket {
        uint256 id;
        address reporter;           // Citizen's Wallet
        ReportType reportType;      // Was it a Photo or Text?
        string evidenceHash;        // IPFS Hash of Photo OR JSON of Text
        string gpsCoordinates;      
        string category;            // "Pothole", "Water Leak"
        uint8 severityScore;        // AI Score (1-10)
        TicketStatus status;
        
        // --- NEW FEATURES ---
        uint256 creationTime;       
        uint256 targetCompletionTime; // AI Estimated Deadline (The "Promise")
        uint256 resolvedTime;         // Actual Fix Time
        string repairProofHash;       // Contractor's "After" Photo
    }

    mapping(uint256 => Ticket) public tickets;
    mapping(address => uint256[]) public userTickets;

    // ============ 3. Events ============
    event TicketCreated(uint256 indexed ticketId, address reporter, uint8 severity, uint256 targetCompletion);
    event TicketResolved(uint256 indexed ticketId, string proofHash);

    // ============ 4. Modifiers ============
    modifier onlyAdmin() {
        require(msg.sender == admin, "Only AI Admin can perform this");
        _;
    }

    constructor() {
        admin = msg.sender; 
    }

    // ============ 5. Functions ============

    /**
     * @notice Creates the "NFT" Claim.
     * @dev Now includes `_targetDurationDays` calculated by your Python AI.
     */
    function createTicket(
        string memory _evidenceHash, 
        string memory _gps, 
        string memory _category,
        uint8 _severity,
        uint8 _reportType,       // 0 for Image, 1 for Text
        uint256 _targetDurationDays // AI passes this in (e.g., 2 days, 7 days)
    ) public {
        uint256 currentId = ticketCounter;

        // Calculate the deadline based on AI estimation
        uint256 completionDeadline = block.timestamp + (_targetDurationDays * 1 days);

        tickets[currentId] = Ticket({
            id: currentId,
            reporter: msg.sender,
            reportType: ReportType(_reportType),
            evidenceHash: _evidenceHash,
            gpsCoordinates: _gps,
            category: _category,
            severityScore: _severity,
            status: TicketStatus.OPEN,
            creationTime: block.timestamp,
            targetCompletionTime: completionDeadline, // Saved on-chain!
            resolvedTime: 0,
            repairProofHash: ""
        });

        userTickets[msg.sender].push(currentId);
        
        emit TicketCreated(currentId, msg.sender, _severity, completionDeadline);
        ticketCounter++;
    }

    /**
     * @notice Contractor/AI validates the fix.
     * @dev This function is called by the Backend after the Contractor uploads a photo.
     */
    function resolveTicket(uint256 _ticketId, string memory _repairProofHash) public onlyAdmin {
        Ticket storage ticket = tickets[_ticketId];
        require(ticket.status != TicketStatus.RESOLVED, "Already resolved");

        ticket.status = TicketStatus.RESOLVED;
        ticket.repairProofHash = _repairProofHash;
        ticket.resolvedTime = block.timestamp;

        emit TicketResolved(_ticketId, _repairProofHash);
    }
    
    // Helper to get all tickets for a user
    function getUserTickets(address _user) external view returns (uint256[] memory) {
        return userTickets[_user];
    }
    
    // Helper to get ticket details
    function getTicket(uint256 _ticketId) external view returns (Ticket memory) {
        return tickets[_ticketId];
    }
}